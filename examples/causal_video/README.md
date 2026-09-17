# Causal video inference: native profiles, GX, and drperf

This study runs pretrained Self-Forcing models through Inferix and FastVideo,
profiles their kernels on an A100, then screens framework overhead with GX
`partial_sync` and drperf in separate runs. It uses the existing Torch 2.11 / CUDA
12.8 environment. Source and model revisions are pinned in `pins.json`.

The [native Inferix comparison](NATIVE_RESULTS.md) measures 41.29 → 12.65 seconds
with byte-identical saved output after selecting GPU KV residency and removing
a discarded decode. A valid baseline drperf instruction summary is recorded
in [the native results](NATIVE_RESULTS.md). The corrected Inferix GX
`partial_sync` run modeled a 12.268-second marked virtual interval; its
[result and fidelity limits](PARTIAL_RESULTS.md) include 168 unmatched cuDNN
plan signatures, so this remains screening evidence.
A native result or kernel database alone is not evidence of a successful GX
timing simulation.

The [matched FastVideo native comparison](FASTVIDEO_NATIVE_RESULTS.md) found
no convincing gain from resident DiT weights: median latency changed from
15.424 to 15.360 seconds, with 2.697 GB more peak allocated GPU memory.
Its [valid drperf collection](FASTVIDEO_DRPERF.md) measures 8.63 billion marked
host instructions; existing RoPE table caching already handles this workload.
The [final FastVideo partial run](FASTVIDEO_PARTIAL_RESULTS.md) models 97.39%
GPU busy time, but 84 cuDNN launch mismatches prevent a matched replay claim.
The [native GPU databases and reports](evidence/kernel-databases/README.md)
are included as small compressed artifacts.

## Workloads and boundaries

- **Inferix:** its public `run_streaming_generation` API, TRUE_STREAMING, the
  pretrained 1.3B Self-Forcing DMD checkpoint, UMT5-XXL, and Wan VAE. The main
  request uses 21 latent frames at 480 × 832 with four denoising steps per block.
  The pinned streaming implementation returns seven chunks of nine pixel frames
  (63 total); this study preserves and reports that behavior.
- **FastVideo:** its public `VideoGenerator.generate_video` API and pretrained
  SFWan causal DMD pipeline, 81 pixel frames at 480 × 832, four denoising steps
  per block. Its prompt differs from Inferix's. The frameworks are independent
  optimization studies, not a controlled quality or throughput comparison.

Load and warmup precede measurement. Generation includes text encoding,
causal denoising, VAE decode, and output transfer; encoding a video file is
excluded. Native tensors are checked for finiteness. GX output values are never
used for numerical validation because GPU arithmetic is skipped.

`native_run.py` uses the existing managed A100 container helper. `config.py`
generates GX managed-launcher configurations; run them using
`GX/NEX/container_cmds/run.py` from that repository. Model assets are staged in
`/workspace/causal`, with the shared Wan checkpoint in the existing workspace.
`asset_identity.py` hashes the actual Inferix checkpoint/tokenizer files on each
host before comparing their identities. FastVideo's downloader records both
source and stored hashes; its fp32 text encoder weights are stored as bf16 to
fit disk, and both native and GX use those same files.
The [runbook](RUNBOOK.md) gives commands for repeating the separate measurements
in these staged workspaces.

## Separate measurements

1. **Native:** warmed, unprofiled A100 generation and saved output.
2. **GPU profile:** a separate real A100 run, profiler enabled only around
   generation. Use zero per-signature profiler warmup after application warmup
   so a signature occurring once still gets a sample. Profiler wall time is not
   the native latency reference.
3. **CPU profile:** GX emulation with native CPU IPC sampling, then `gxvm collect`.
4. **Partial timing:** GX `partial_sync` with the GPU and CPU databases; obtain
   virtual iteration durations from `gxvm report`, not application clocks.
   FastVideo's timeline markers are in its GPU worker. The public parent call
   also builds frame grids after the worker responds, so its worker virtual
   interval is not the full parent-call latency.
5. **drperf:** GX emulation without GX timing instrumentation. The drperf CUDA
   boundary excludes emulated CUDA calls in `gx_cuda.so`; application/library
   host dispatch remains measured. Markers cover transformer, attention, RoPE,
   VAE, and KV cache regions. Check drperf validity before interpreting counts.
6. **Validation:** compare candidate and baseline native outputs and repeat
   warmed unprofiled timings. `validate_inferix.py` additionally captures
   callbacks, latent tensors, and final VAE cache state; these extra copies make
   its host timings unsuitable as performance results.

## Adaptations must remain visible

`prepare_inferix.py` makes unused UI imports lazy. `compat.py` handles the
removed torchvision video writer and the Diffusers single-GPU configuration
keyword collision. Memory-mapped checkpoint reads reduce setup RAM without
changing the state dictionary or measured generation.

`inferix_metadata.py` moves token lengths and Python KV-cache position counters
to host storage. GX needs actual control metadata even though it skips GPU
arithmetic. This change also removes real GPU synchronization costs, so native
and GX comparisons must use the same adapted source. Retain original native
results separately and validate the adaptation numerically.

`inferix_decode.py` is a candidate patch: TRUE_STREAMING already decodes every
block, but the pinned code also decodes the whole sequence and discards that
second result. The patch skips only that redundant decode. Source inspection
is a lead; native semantic validation and measured results are required before
claiming an optimization.

## Interpreting partial_sync

The timeline retains GPU stream/event dependencies and CPU work, but does not
reconstruct all CPU synchronization. Memcpy/memset service and some other costs
are omitted; a missing kernel prediction contributes zero time. It is an
optimistic approximation, **not a guaranteed hardware lower bound**.

`summarize_partial.py` reports marked intervals, prediction coverage, CPU
sampling coverage, device busy/idle spans, and large CPU segments before GPU
submissions. CPU/GPU work sums can overlap: neither their sums nor an idle span
alone proves a CPU bottleneck. Validate suspicious regions with drperf and
real A100 measurements. Launch-inventory comparison is an additional gate;
matching shapes and counts cannot prove numerical equivalence.

For each partial run, require successful managed cleanup, a completed model
report with the intended measured request (21 latent frames for Inferix; 81
pixel frames for FastVideo), a nonempty marked virtual
interval from `gxvm report`, no CPU IPC coverage/trace errors, and kernel
prediction hits for every measured launch. Select trace launches by host
`create_ts_us` inside the worker's measured host interval: the task `ts`
switches to a logical clock after adoption. `audit_kernel_trace.py` checks
native-profile versus GX source/settings, launch counts, unambiguous
signatures, metadata, usable samples and hit status. A failed inventory gate
means the virtual duration cannot be presented as a matched replay. The
currently configured Inferix GPU profile has 106,617 observed API rows,
including 8,838 cuBLAS wrapper rows. Its 97,779 non-cuBLAS kernel launches
match the prior 21-frame GX CPU-profile count, but only 97,611 match at the
exact signature; 168 use different cuDNN bf16/tf32 plan variants. Those
variants still fail the [Inferix partial audit](PARTIAL_RESULTS.md). The cuBLAS
wrapper audit found one GX surrogate task per intercepted call, without nested
emulated `cuLaunch*` work; matching that wrapper count does not resolve the
cuDNN signature differences.

CPU calibration currently runs on the GX host (AMD EPYC 7702P), whereas the
A100 host has AMD EPYC 9554 CPUs. Partial timings are therefore screening
estimates for this calibration, not calibrated predictions of the A100 host.
CPU instruction counts remain a separate measurement from CPU elapsed time.

The current Inferix GX-host IPC shard recorded 14,390 resolved instruction
samples and 6,684 unresolved samples: **31.7% of all instruction samples**
were unresolved (`6,684 / (14,390 + 6,684)`). The unresolved count is 46.4%
*relative to resolved samples*, a different denominator. The collector maps
sampled instruction pointers to executable file mappings when it writes the
profile; anonymous/JIT code and mappings gone by then can remain unresolved.
Its fallback cost is therefore material. `native_cpu_inferix_entry.py` prepares
an opt-in measurement of real GPU generation on the A100 host after warmup,
but the managed native container currently has `perf_event_paranoid=4`, no
effective capabilities, and no staged native IPC profiler library. Native CPU
profiling is unavailable under that configuration.

A native-host profile would measure 9554 CPU costs, but would not by itself
prove replay fidelity on the 7702P GX host. GXVM indexes CPU cost by hash of
the absolute mapped module path and a 4 KiB page offset, then falls back to
module or global means. The database does not verify binary identity or ISA
dispatch. Native GPU and GX emulation can execute different host paths; Torch
or libc may also select different code on Zen 4 and Zen 2. Compare module
paths/builds, measured launch inventory, replay page/module/global coverage,
and real A100 times before treating a partial estimate as calibrated.
