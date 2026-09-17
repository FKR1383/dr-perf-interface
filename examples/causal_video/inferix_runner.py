"""Full pretrained Inferix Self Forcing streaming workload with explicit boundaries."""
import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--role', choices=['native', 'gpu-profile', 'emu', 'cpu-profile', 'partial_sync', 'drperf'], required=True)
    p.add_argument('--tree', required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--latent-frames', type=int, default=21)
    p.add_argument('--segments', type=int, default=1)
    p.add_argument('--warmup-frames', type=int, default=3)
    p.add_argument('--save-output', action='store_true')
    p.add_argument('--repetitions', type=int, default=1)
    p.add_argument('--kv-residency', choices=['offload','gpu'], default='offload')
    a = p.parse_args()
    assert a.repetitions >= 1
    assert a.repetitions == 1 or a.role == 'native'
    a.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, a.tree)
    from compat import install
    install()
    import torch
    from omegaconf import OmegaConf
    from inferix.pipeline.self_forcing.pipeline import SelfForcingPipeline
    from inferix.models.wan_base.utils.parallel_config import ParallelConfig
    from inferix.core.types import StreamingMode
    from compat import install_inferix_loader
    install_inferix_loader()
    torch.set_num_threads(1)
    torch.set_grad_enabled(False)
    torch.manual_seed(42)
    physical = a.role in ('native', 'gpu-profile')
    maps = Path('/proc/self/maps').read_text()
    assert ('gx_cuda.so' not in maps) == physical
    config = OmegaConf.merge(
        OmegaConf.load(Path(a.tree)/'example/self_forcing/configs/default_config.yaml'),
        OmegaConf.load(Path(a.tree)/'example/self_forcing/configs/self_forcing_dmd.yaml'))
    config.model_path = a.base
    if 'model_kwargs' not in config:
        config.model_kwargs = {}
    config.model_kwargs.enable_kv_offload = a.kv_residency == 'offload'
    OmegaConf.save(config, a.output/'config.yaml')
    report = dict(role=a.role, pid=os.getpid(), source_tree=a.tree,
                  source_sha256={str(f.relative_to(a.tree)):hashlib.sha256(f.read_bytes()).hexdigest()
                                 for f in sorted(Path(a.tree,'inferix').rglob('*.py'))},
                  packages={k:importlib.metadata.version(k) for k in ['torch','torchvision','transformers','diffusers','flash-attn']},
                  latent_frames=a.latent_frames, segments=a.segments, seed=42,
                  warmup_frames=a.warmup_frames, repetitions=a.repetitions, kv_residency=a.kv_residency,
                  harness_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),Path(__file__).with_name('compat.py')]},
                  cudnn_version=torch.backends.cudnn.version(),
                  cudnn_policy=dict(enabled=torch.backends.cudnn.enabled, benchmark=torch.backends.cudnn.benchmark, deterministic=torch.backends.cudnn.deterministic),
                  prompt='A cat walks on the grass, realistic style',
                  streaming_mode='TRUE_STREAMING', low_memory=False,
                  clock='host_perf_counter_ns', phases=[], chunks=[])
    identity=Path(__file__).resolve().parent.parent/'inferix-assets.json'
    if identity.is_file():
        report['asset_identity']=json.loads(identity.read_text())
    def save():
        (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    save()
    started = time.perf_counter()
    pipe = SelfForcingPipeline(str(a.output/'config.yaml'), parallel_config=ParallelConfig())
    pipe.load_checkpoint(a.checkpoint, use_ema=True)
    pipe.setup_devices(low_memory=False, verbose=True, use_memory_manager=False)
    torch.cuda.synchronize()
    report['load_host_seconds'] = time.perf_counter()-started
    active = False
    def trace(obj, method, label):
        original = getattr(obj, method)
        def wrapped(*args, **kwargs):
            if not active:
                return original(*args, **kwargs)
            start = time.perf_counter_ns()
            shape = list(args[0].shape) if args and isinstance(args[0], torch.Tensor) else None
            result = original(*args, **kwargs)
            report['phases'].append(dict(name=label, start_ns=start, end_ns=time.perf_counter_ns(), input_shape=shape))
            return result
        setattr(obj, method, wrapped)
    trace(pipe.pipeline.text_encoder, 'forward', 'text_encoder')
    trace(pipe.pipeline.generator, 'forward', 'transformer')
    trace(pipe.pipeline.vae, 'decode_to_pixel', 'vae_decode')
    def chunk(frames):
        if active:
            report['chunks'].append(dict(host_ns=time.perf_counter_ns(), shape=list(frames.shape)))
    def generate(frames, segments):
        torch.manual_seed(42)
        return pipe.run_streaming_generation(
            prompts=[report['prompt']], stream_callback=chunk, num_segments=segments,
            segment_length=frames, overlap_frames=3, num_samples=1,
            low_memory=False, streaming_mode=StreamingMode.TRUE_STREAMING)
    if a.warmup_frames:
        warm = generate(a.warmup_frames, 1)
        torch.cuda.synchronize()
        if physical:
            assert torch.isfinite(warm).all().item()
        del warm
    print('CAUSAL_WARMUP_DONE', flush=True)
    if a.role == 'drperf':
        from instrument_inferix import install as install_instrumentation
        report['regions'] = install_instrumentation(pipe)
    runtime = ctypes.CDLL(None)
    if a.role == 'gpu-profile':
        Path(os.environ['GX_PROFILE_START_FILE']).touch(exist_ok=False)
    elif a.role == 'cpu-profile':
        runtime.gxvm_ipc_profile_start()
    elif a.role == 'partial_sync':
        runtime.gxvm_adopt_now()
        runtime.gxvm_timeline_mark.argtypes = [ctypes.c_uint, ctypes.c_int]
        runtime.gxvm_timeline_mark(1, 0)
    active = True
    if physical:
        torch.cuda.reset_peak_memory_stats()
    report['start_host_ns'] = time.perf_counter_ns()
    report['iterations'] = []
    for iteration in range(a.repetitions):
        begin = time.perf_counter_ns()
        video = generate(a.latent_frames, a.segments)
        torch.cuda.synchronize()
        finish = time.perf_counter_ns()
        report['iterations'].append(dict(iteration=iteration,start_host_ns=begin,end_host_ns=finish,host_seconds=(finish-begin)/1e9))
    report['end_host_ns'] = time.perf_counter_ns()
    active = False
    if a.role == 'gpu-profile':
        Path(os.environ['GX_PROFILE_STOP_FILE']).touch(exist_ok=False)
    elif a.role == 'cpu-profile':
        assert runtime.gxvm_ipc_profile_stop() == 0
    elif a.role == 'partial_sync':
        runtime.gxvm_timeline_mark(1, 1)
    report['generation_host_seconds'] = sum(x['host_seconds'] for x in report['iterations'])/a.repetitions
    report['shape'] = list(video.shape)
    report['finite_checked'] = physical
    if physical:
        report['peak_gpu_allocated_bytes'] = torch.cuda.max_memory_allocated()
        report['peak_gpu_reserved_bytes'] = torch.cuda.max_memory_reserved()
        report['finite'] = bool(torch.isfinite(video).all().item())
        assert report['finite']
        report['mean'] = video.float().mean().item()
        report['std'] = video.float().std().item()
        if a.save_output:
            torch.save(video.cpu(), a.output/'video.pt')
    save()
    print('CAUSAL_RESULT', json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','phases']}), flush=True)

if __name__ == '__main__':
    main()
