"""Run the FastVideo SelfForcing causal workload in native or GX environments.

The measured interval contains one complete 81-frame generation, including
text encoding, all causal denoising blocks, VAE decode, and output transfer.
"""

import argparse
import contextlib
import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

_nsys_worker_marks = 0
_worker_mark_calls = 0


def worker_sync(worker, metadata_mode=False, capture_cudnn_dso=False):
    import torch
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    compat = None
    if metadata_mode:
        from fastvideo_metadata import install
        compat = install(worker)
    torch.cuda.synchronize()
    args = worker.worker.fastvideo_args
    transformer = worker.worker.pipeline.get_module("transformer")
    first_block = transformer.blocks[0]
    details = {"pid": os.getpid(), "gpu": torch.cuda.get_device_name(0), "metadata_changes": compat,
            "dit_layerwise_offload": args.dit_layerwise_offload,
            "dit_cpu_offload": args.dit_cpu_offload,
            "worker_cpu_output": os.environ.get("FASTVIDEO_WORKER_CPU_OUTPUT") == "1",
            "attention_backend": {"self": first_block.attn1.attn.backend.name,
                                  "cross": first_block.attn2.attn.backend.name},
            "torch_threads": torch.get_num_threads(),
            "torch_interop_threads": torch.get_num_interop_threads(),
            "cudnn_version": torch.backends.cudnn.version(),
            "cudnn_policy": {"enabled": torch.backends.cudnn.enabled,
                             "benchmark": torch.backends.cudnn.benchmark,
                             "deterministic": torch.backends.cudnn.deterministic}}
    if capture_cudnn_dso:
        paths = {line.rsplit(None, 1)[-1] for line in Path("/proc/self/maps").read_text().splitlines()
                 if "/libcudnn" in line and ".so" in line}
        digests = {}
        for path in sorted(paths):
            if Path(path).is_file():
                with open(path, "rb") as library:
                    digests[Path(path).name] = hashlib.file_digest(library, "sha256").hexdigest()
        details["cudnn_dso_sha256"] = digests
    return details


def worker_mark(worker, adopt=False, timeline_end=None):
    global _nsys_worker_marks, _worker_mark_calls
    import torch
    runtime = ctypes.CDLL(None)
    if adopt:
        runtime.gxvm_adopt_now.argtypes = []
        runtime.gxvm_adopt_now()
    torch.cuda.synchronize()
    _worker_mark_calls += 1
    if os.environ.get("GX_COMM_ONLY") != "1" and _worker_mark_calls == 1:
        torch.cuda.reset_peak_memory_stats()
    if os.environ.get("FASTVIDEO_NSYS_CAPTURE") == "1":
        _nsys_worker_marks += 1
        if _nsys_worker_marks == 1:
            assert torch.cuda.cudart().cudaProfilerStart() == 0
        elif _nsys_worker_marks == 2:
            assert torch.cuda.cudart().cudaProfilerStop() == 0
        else:
            raise RuntimeError(f"Expected two Nsight worker markers, got {_nsys_worker_marks}")
    if timeline_end is not None:
        runtime.gxvm_timeline_mark.argtypes = [ctypes.c_uint, ctypes.c_int]
        runtime.gxvm_timeline_mark(1, int(timeline_end))
    marker = {"pid": os.getpid(), "host_ns": time.perf_counter_ns()}
    if os.environ.get("GX_COMM_ONLY") != "1":
        marker["gpu_memory_bytes"] = {
            "allocated": torch.cuda.memory_allocated(),
            "reserved": torch.cuda.memory_reserved(),
            "peak_allocated": torch.cuda.max_memory_allocated(),
            "peak_reserved": torch.cuda.max_memory_reserved(),
        }
    if os.environ.get("GX_COMM_ONLY") == "1":
        runtime.gxvm_time_ns.argtypes = []
        runtime.gxvm_time_ns.restype = ctypes.c_uint64
        marker["gx_ns"] = runtime.gxvm_time_ns()
    return marker


def worker_profile_start(worker):
    runtime = ctypes.CDLL(None)
    runtime.gxvm_ipc_profile_start.argtypes = []
    runtime.gxvm_ipc_profile_start.restype = ctypes.c_int
    return runtime.gxvm_ipc_profile_start()


def worker_profile_stop(worker):
    runtime = ctypes.CDLL(None)
    runtime.gxvm_ipc_profile_stop.argtypes = []
    runtime.gxvm_ipc_profile_stop.restype = ctypes.c_int
    return runtime.gxvm_ipc_profile_stop()


def worker_install_instrumentation(worker):
    from instrument_fastvideo import install
    return install(worker)


def worker_drperf_attach(worker):
    """Attach before warmup creates additional CUDA/PyTorch worker threads.

    The region is deliberately outside the measured generation. DynamoRIO's
    late attach must take over all threads already alive in this process, even
    when the drperf client is configured to count only the calling thread.
    """
    import perfmark
    with perfmark.region("fastvideo_attach_setup"):
        pass
    return {"pid": os.getpid()}


def wait_for_gx_trace_export(generator, timeout_seconds=120):
    """Let GX workers finish their atexit trace write before framework cleanup.

    FastVideo's normal shutdown SIGTERMs workers after five seconds, which can
    truncate a large Chrome trace. This runs after all measurement markers.
    The ordinary shutdown remains the fallback if the grace period expires.
    """
    workers = list(generator.executor.workers)
    start = time.monotonic()
    deadline = start + timeout_seconds
    for worker in workers:
        with contextlib.suppress(Exception):
            worker.pipe.send({"method": "shutdown", "args": (), "kwargs": {}})
    for worker in workers:
        with contextlib.suppress(Exception):
            worker.proc.join(timeout=max(0.0, deadline - time.monotonic()))
    return {"timeout_seconds": timeout_seconds,
            "elapsed_seconds": time.monotonic() - start,
            "worker_pids": [worker.proc.pid for worker in workers],
            "workers_exited": [not worker.proc.is_alive() for worker in workers]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True,
                        choices=("native", "gpu-profile", "emu", "cpu-profile", "partial_sync", "drperf"))
    parser.add_argument("--tree", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames", type=int, default=81)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--metadata-mode", action="store_true")
    parser.add_argument("--resident-dit", action="store_true",
                        help="Keep DiT block weights on GPU instead of default layerwise CPU offload")
    parser.add_argument("--worker-cpu-output", action="store_true",
                        help="Transfer generated output to CPU in the worker before IPC")
    args = parser.parse_args()
    assert args.repetitions >= 1
    assert args.repetitions == 1 or args.role == "native"
    if args.worker_cpu_output:
        os.environ["FASTVIDEO_WORKER_CPU_OUTPUT"] = "1"
    else:
        assert os.environ.get("FASTVIDEO_WORKER_CPU_OUTPUT") != "1"

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    tree = Path(args.tree).resolve()
    model = Path(args.model).resolve()
    sys.path.insert(0, str(tree))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from compat import install
    install()
    import torch
    from fastvideo import SamplingParam, VideoGenerator

    assert Path(sys.modules["fastvideo"].__file__).resolve().is_relative_to(tree)
    assert model.is_dir()
    assert "A100" in torch.cuda.get_device_name(0)
    physical = args.role in ("native", "gpu-profile")
    assert (os.environ.get("GX_COMM_ONLY") == "1") != physical
    maps = Path("/proc/self/maps").read_text()
    if physical:
        assert "gx_cuda.so" not in maps and "libdynamorio" not in maps
    else:
        assert "gx_cuda.so" in maps
        assert args.metadata_mode, "GX runs require the matched --metadata-mode path"
    if args.role == "gpu-profile":
        assert os.environ.get("GX_PROFILE_DB")
        for key in ("GX_PROFILE_START_FILE", "GX_PROFILE_STOP_FILE"):
            assert os.environ.get(key) and not Path(os.environ[key]).exists()

    prompt = ("A curious raccoon peers through a vibrant field of yellow sunflowers, "
              "its eyes wide with interest. Soft natural light, mid-shot, realistic style.")
    sampling = SamplingParam.from_pretrained("wlsaidhi/SFWan2.1-T2V-1.3B-Diffusers")
    sampling.update(dict(num_frames=args.frames, height=args.height, width=args.width,
                         num_inference_steps=4, seed=args.seed, save_video=False,
                         return_frames=True))
    report = dict(role=args.role, metadata_mode=args.metadata_mode,
                  repetitions=args.repetitions,
                  resident_dit=args.resident_dit,
                  worker_cpu_output=args.worker_cpu_output,
                  stage_verification_enabled=not args.metadata_mode,
                  model=str(model), tree=str(tree), prompt=prompt,
                  sampling=dict(frames=args.frames, height=args.height, width=args.width,
                                steps=4, seed=args.seed, fps=sampling.fps,
                                guidance_scale=sampling.guidance_scale),
                  gpu=torch.cuda.get_device_name(0),
                  cudnn_version=torch.backends.cudnn.version(),
                  cudnn_policy=dict(enabled=torch.backends.cudnn.enabled,
                                    benchmark=torch.backends.cudnn.benchmark,
                                    deterministic=torch.backends.cudnn.deterministic),
                  packages={key: importlib.metadata.version(key) for key in
                            ("torch", "torchvision", "transformers", "diffusers", "safetensors")},
                  source_sha256={str(path.relative_to(tree)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted((tree / "fastvideo").rglob("*.py"))},
                  metadata_source_sha256=(
                      hashlib.sha256((Path(__file__).parent / "fastvideo_metadata.py").read_bytes()).hexdigest()
                      if args.metadata_mode else None),
                  instrumentation_source_sha256=(
                      hashlib.sha256((Path(__file__).parent / "instrument_fastvideo.py").read_bytes()).hexdigest()
                      if args.role == "drperf" else None),
                  environment={key: value for key, value in sorted(os.environ.items())
                               if key.startswith(("GXVM_", "GX_PREDICT_", "GX_PROFILE_",
                                                  "GX_DEVICE_", "GX_REAL_", "GX_CUDA_"))
                               or key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                          "OPENBLAS_NUM_THREADS", "PYTHONHASHSEED",
                                          "FASTVIDEO_ATTENTION_BACKEND", "TOKENIZERS_PARALLELISM",
                                          "LD_LIBRARY_PATH", "FASTVIDEO_WORKER_CPU_OUTPUT")})

    def save():
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    save()
    load_start = time.perf_counter()
    generator_kwargs = dict(num_gpus=1, use_fsdp_inference=False,
                            text_encoder_cpu_offload=False, dit_cpu_offload=False,
                            vae_cpu_offload=False, text_encoder_precisions=("bf16",))
    if args.resident_dit:
        generator_kwargs["dit_layerwise_offload"] = False
    generator = VideoGenerator.from_pretrained(str(model), **generator_kwargs)
    report["worker"] = generator.executor.collective_rpc(
        worker_sync, kwargs={"metadata_mode": args.metadata_mode})
    report["load_seconds"] = time.perf_counter() - load_start
    save()
    print("FASTVIDEO_LOADED", report["load_seconds"], flush=True)

    if args.role == "drperf":
        report["drperf_attach"] = generator.executor.collective_rpc(worker_drperf_attach)
        save()
        print("FASTVIDEO_DRPERF_ATTACHED", report["drperf_attach"], flush=True)

    def generate():
        return generator.generate_video(prompt, sampling_param=sampling,
                                        output_path=str(out), save_video=False,
                                        return_frames=True)

    try:
        warmup = generate()
        report["worker"] = generator.executor.collective_rpc(
            worker_sync, kwargs={"metadata_mode": args.metadata_mode,
                                 "capture_cudnn_dso": True})
        report["warmup"] = summarize(warmup, args, physical)
        del warmup
        save()
        print("FASTVIDEO_WARMUP_DONE", flush=True)

        if args.role == "drperf":
            report["regions"] = generator.executor.collective_rpc(worker_install_instrumentation)
            save()

        if args.role == "gpu-profile":
            Path(os.environ["GX_PROFILE_START_FILE"]).touch(exist_ok=False)
        elif args.role == "cpu-profile":
            assert generator.executor.collective_rpc(worker_profile_start) == [0]
        elif args.role == "partial_sync":
            runtime = ctypes.CDLL(None)
            runtime.gxvm_adopt_now.argtypes = []
            runtime.gxvm_adopt_now()
        report["worker_start"] = generator.executor.collective_rpc(
            worker_mark, kwargs={"adopt": args.role == "partial_sync",
                                 "timeline_end": False if args.role == "partial_sync" else None})
        start = time.perf_counter_ns()
        report["iterations"] = []
        for iteration in range(args.repetitions):
            iteration_start = time.perf_counter_ns()
            result = generate()
            iteration_end = time.perf_counter_ns()
            report["iterations"].append({"iteration": iteration,
                                         "elapsed_seconds": (iteration_end - iteration_start) / 1e9})
        report["worker_end"] = generator.executor.collective_rpc(
            worker_mark, kwargs={"timeline_end": True if args.role == "partial_sync" else None})
        end = time.perf_counter_ns()
        if args.role == "gpu-profile":
            Path(os.environ["GX_PROFILE_STOP_FILE"]).touch(exist_ok=False)
        elif args.role == "cpu-profile":
            assert generator.executor.collective_rpc(worker_profile_stop) == [0]
        report["elapsed_seconds"] = (end - start) / 1e9
        report["mean_iteration_seconds"] = sum(
            item["elapsed_seconds"] for item in report["iterations"]) / args.repetitions
        report["parent_interval_ns"] = [start, end]
        report["worker_interval_host_seconds"] = (
            report["worker_end"][0]["host_ns"] - report["worker_start"][0]["host_ns"]) / 1e9
        if "gx_ns" in report["worker_start"][0]:
            report["worker_interval_gx_seconds"] = (
                report["worker_end"][0]["gx_ns"] - report["worker_start"][0]["gx_ns"]) / 1e9
        report["result"] = summarize(result, args, physical)
        if physical:
            video_path = out / "video-fp16.pt"
            torch.save(result["samples"].to(torch.float16), video_path)
            report["saved_video"] = dict(path=str(video_path), bytes=video_path.stat().st_size,
                                         sha256=hashlib.file_digest(video_path.open("rb"), "sha256").hexdigest())
        save()
        print("FASTVIDEO_RESULT", json.dumps({key: report[key] for key in
                                               ("role", "elapsed_seconds", "result")}), flush=True)
    finally:
        try:
            if not physical and os.environ.get("GX_CHROME_TRACE") == "1":
                report["gx_trace_cleanup"] = wait_for_gx_trace_export(generator)
                save()
        finally:
            generator.shutdown()


def summarize(result, args, physical):
    import torch
    import numpy as np

    assert isinstance(result, dict), type(result)
    samples = result["samples"]
    expected = (1, 3, args.frames, args.height, args.width)
    assert tuple(samples.shape) == expected, (tuple(samples.shape), expected)
    summary = dict(shape=list(samples.shape), dtype=str(samples.dtype),
                   generation_time=result.get("generation_time"),
                   e2e_latency=result.get("e2e_latency"))
    if physical:
        summary["finite"] = bool(torch.isfinite(samples).all().item())
        assert summary["finite"]
        summary["mean"] = float(samples.float().mean())
        summary["std"] = float(samples.float().std())
        assert np.isfinite(summary["mean"]) and np.isfinite(summary["std"])
    return summary


if __name__ == "__main__":
    main()
