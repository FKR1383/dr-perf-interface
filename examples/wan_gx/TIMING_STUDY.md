# Wan: trace-guided CPU optimization with fixed GPU kernels

On the full pretrained Wan pipeline, drperf-guided CPU changes reduced marked
instructions by **15.39%**. One paired GXVM replay measured **195.75110 ->
195.02873 virtual seconds**, a **0.369%** reduction. The ordered sequence of
all **359,473 GPU launches/BLAS operations** and their recorded metadata stayed
identical. Both replays had zero prediction misses or errors.

This is a simulation case study. GX skips GPU arithmetic. The earlier
[native A100 comparison](NATIVE_RESULTS.md) is a separate experiment with
other optimizations; its Conv3d and RMSNorm replacements are excluded here.

| Measurement | Baseline | CPU optimized |
| --- | ---: | ---: |
| Marked own CPU instructions | 18,581,951,706 | 15,721,327,813 |
| `model.to(device)` calls | 50 | 1 |
| Instructions in those residency walks | 2,352,966,688 | 46,792,783 |
| Transformer-block own instructions | 2,846,827,912 | 2,299,404,648 |
| End-to-end virtual seconds | 195.75110 | 195.02873 |
| Recorded stream task seconds | 194.98251 | 194.98254 |
| Recorded stream gap seconds | 0.76859 | 0.04619 |
| Summed predicted kernel seconds | 193.534945467 | 193.534945467 |
| Prediction hits / virtual waits | 359,473 / 359,473 | 359,473 / 359,473 |
| Prediction misses / errors | 0 / 0 | 0 / 0 |

## What the feedback changed

The baseline timing trace showed repeated gaps of about 15 ms ending just
before transformer work. drperf attributed 2.353 billion instructions to 50
model-residency walks. The model already stays on the same device throughout
denoising, so [the application patch](optimization-timing-cpu.patch) moves the
walk before the loop. It also removes three redundant precision scopes per
transformer block and an unnecessary local function. The removed scopes contain
only CUDA autocast fallthrough operations. Explicit float32-disabled scopes
remain around the linear layers, using the current PyTorch API.

Afterward, the repeated gaps disappear; the single initial residency walk
remains. Stream gaps shrink by 0.72240 seconds, accounting for essentially all
of the 0.72237-second end-to-end change. Recorded stream task time changes by
only 30 us. The GPU work dominates: FlashAttention contributes 101.37 seconds
of predicted latency, and cuBLASLt matmuls contribute 36.75 seconds. Removing
more CPU instructions from work already overlapped with that GPU activity
would not imply a comparable end-to-end improvement.

This demonstrates the intended loop: use the timing trace to locate exposed
CPU work, use drperf to quantify the responsible regions, validate the rewrite
in emulation, then replay timing with the GPU kernels held fixed.

## Workload and measurement boundaries

- Official Wan source `9737cba9c1c3c4d04b33fcad41c111989865d315` and
  Wan-AI/Wan2.1-T2V-1.3B checkpoint revision
  `37ec512624d61f7aa208f7ea8140a131f93afc9a`.
- UMT5-XXL text encoding, all 30 transformer layers, UniPC and complete VAE
  decode: 832 x 480, 81 frames, 50 steps, CFG 5, shift 5, seed 42, no offload.
  Prompt: `A cat walks on the grass, realistic style`.
- Both variants include [metadata.patch](metadata.patch). cuDNN stays enabled.
  Initialization and four full-shape warmup steps precede measurement.
- GPU profiling ran on physical A100 PCIe 40GB GPU1 only. Subsequent optimization
  runs used GX on `icdslab2.epfl.ch`, an AMD EPYC 7702P host, with an 8-CPU/64-GB
  container limit and one PyTorch/BLAS thread. The native container is stopped.
- CPU profiling, drperf and timing replay are separate runs. CPU collection has
  explicit start/stop markers. Replay uses the same CPU database, 10-us epochs,
  refund accounting and CPU cost scale 1 for both variants. GX's existing
  stream-worker bookkeeping scaling is 30x; measured GPU latencies are unscaled.
  HBM mode enables compute waits; this workload has no NCCL traffic.

## Validation and limits

The [compact comparison](evidence/timing-comparison.json) preserves reports,
region counts, source hashes, artifact hashes, controller completion and timing
policy. Every controller passed and drained without cleanup errors. Both
replays used the same immutable GX/GXVM runtime bundle.

The native profile contains 297 signatures and 2,441 usable timing samples.
The full native/emulated inventories match names, grids, blocks, available
metadata and counts, with no ambiguous predictor keys or signatures lacking
samples. Baseline and optimized replay have the same per-stream sequence hash.
Fifteen framework/CUDA libraries, including FlashAttention, match byte-for-byte
between native profiling and emulation. The inventory mixes individual kernels
and timed cuBLAS API operations, whose internal kernels are encapsulated by
those timings. It does not compare arbitrary kernel argument values.

[test_timing_cpu.py](test_timing_cpu.py) passes 12 nonzero transformer comparisons
with exact CPU outputs and identical tensor-operation sequences: batches 1/2,
padding 0/3 and three timesteps. It also checks CUDA autocast dispatcher policy.
These checks passed inside the benchmark container with PyTorch 2.11.0+cu128.
The full optimized pretrained model completes emulation with the expected video
shape. Full real-GPU numerical/perceptual equivalence was not measured.

The drperf runs have no counter overflow, dropped states, unmatched ends or GX
module residue. They exclude GX CUDA exports and synchronous callees, plus
unmarked worker threads. Counts are marked caller-thread work, including
annotation overhead. Most fixed-shape regions have insufficient distinct PCV
states for an affine fit; this case does not claim that every performance
interface passed an unexplained-cost threshold.

The CPU profile has 39,515 resolved instruction samples and 8,616 resolved task
samples, plus 10,617 and 12 unresolved samples. Its reported 99.906% qualified
coverage is among resolved instruction samples; 21.18% of all instruction
samples remain unresolved. Stream task durations include epoch rounding and
simulator bookkeeping, and stream gaps are not a direct measurement of CPU
execution time. These are experimental model results from one paired replay,
not a statistical hardware speedup estimate or a validated reproduction of
the A100 server's CPU performance.

## GX repairs needed to make the comparison reviewable

[The isolated overlay](gx_patches/cudnn-host-dispatch.patch) and its
[source hashes](gx_patches/source-sha256.json) preserve the runtime changes.
The shared GX checkout was not edited. The overlay:

- Runs the installed cuDNN host dispatch and repairs context, module,
  stream/event and extended-launch handle plumbing. Native probes establish
  the private current-context/unique-ID queries required by cuBLASLt.
- Forwards batched cuBLAS host dispatch through a real host handle while CUDA
  execution stays emulated. Otherwise T5's 96 batched GEMM launches vanished.
- Keeps the native profiler's resolver hooks when CUDA resolves
  `cuGetProcAddress` through itself. Otherwise spatial convolution launches
  escaped collection despite a zero-skip summary.
- Reads the shared simulation clock explicitly for stream tracing after
  adoption. An earlier trace mixed host and virtual clocks and had 5,529
  negative-duration prediction events; that trace was rejected.

These are development patches tested on this workload, not a general GX
compatibility claim. Context identity, small Conv3d dispatch and actual T5
attention einsum probes are included beside this document.

## Reproduction and traces

The [preserved inputs](evidence/timing-inputs/README.md) include the compressed
GPU database, CPU profile, native device queries and library fingerprints:

```bash
python3 examples/wan_gx/unpack_timing_inputs.py out/wan-timing/inputs
```

Use the guides under `~/GX/NEX/usage/` to prepare the
matching image, model assets and runtime. `prepare_cudnn_runtime.py` applies the
patch to a fresh overlay after checking its base hashes. In this workspace it
was built with:

```bash
cd out/wan-timing/gx-cudnn-source
bazel build --jobs=8 \
  --override_repository=+_repo_rules+cuda_headers=/home/ubuntu/drperf/out/wan-timing/cuda-headers \
  --linkopt=-L/home/ubuntu/drperf/out/wan-timing/build-libs \
  //src/sims/gpu:gx_cuda.so //src/profile:gx_profile.so
```

`optimize_timing_cpu.py` prepares a fresh `out/wan-gx/timing-cpu` tree from the
boundary-fixed baseline and writes the reviewable patch. Stage both model
trees and the checkpoint in the managed host workspace. `timing_config.py`
generates `cpu-profile`, `drperf`, `emu` and `replay` configurations. Supply
`--real-cudnn`, the patched `--gx-library`, `--context-limits`,
`--device-attributes` and `--gpu-db` in every mode; the GPU database is also
needed for native function-query replay when timing is disabled. Replay adds
`--cpu-db`. drperf adds a directory prepared by `prepare_drperf_bundle.py`.

Launch from the GX checkout through the managed helper:

```bash
SSH_BASE_PORT=24420 python3 container_cmds/run.py /absolute/path/to/experiment.json
```

Collect only the CPU profile shard named by the application report's PID:
`python3 /home/ubuntu/GX/NEX/tools/gxvm/gxvm collect DIRECTORY`.
The installed `/usr/local/bin/gxvm` on this system predates that subcommand.
`audit_kernel_trace.py`, `analyze_timing_trace.py` and `report_timing.py` apply
the inventory, clock, prediction, source-change and paired-input checks.

Raw local results are under `out/wan-timing/`:

| Evidence | Directory | Managed run ID |
| --- | --- | --- |
| Baseline CPU profile | `baseline-cpu-clock-db-result` | `1789583256532777028` |
| Baseline timing | `baseline-replay-clock-result` | `1789583521307047090` |
| Baseline drperf | `baseline-drperf-db-result` | `1789584046890044733` |
| Optimized drperf and CPU tests | `cpu-drperf-db-result` | `1789584465559740349` |
| Optimized timing | `cpu-replay-clock-result` | `1789584897170650337` |

Each timing directory contains `measured-trace.json.gz`: the measured interval
with aligned CPU submission ranges, suitable for a Chrome-trace viewer.
The full unfiltered trace also retains native warmup timestamps. GPU profiling
artifacts are in `out/wan-timing/gpu-profile/resolver/`; retain the raw profile's
`observed_launches` table rather than discarding it through a generic merge.
