# Real Wan inference under GX, with drperf feedback

This experiment runs the official pretrained **Wan2.1-T2V-1.3B** pipeline:
UMT5-XXL text encoding, all 30 transformer layers, classifier-free guidance,
UniPC scheduling, and VAE decode. The full case uses 832x480, 81 frames,
50 denoising steps, seed 42, and no model offload. GX skips GPU computation;
these are structural executions of the actual model, not generated-video
correctness tests or GPU latency measurements. Timing simulation is off.
See [the measured comparison](RESULTS.md) and [pinned provenance](evidence/provenance.json).
The [further optimization passes](MORE_RESULTS.md) extend the initial 19.84%
instruction reduction to 39.12%, while preserving the first-pass code and evidence.
The subsequent [real A100 comparison](NATIVE_RESULTS.md) measured 218.88 s versus
207.43 s for one full generation per variant (5.23% lower latency). The outputs
differ; numerical and perceptual equivalence remain unestablished.

## Boundary repairs shared by both variants

The original application cannot complete this workload in this GX image.
[metadata.patch](metadata.patch) makes control metadata independent of skipped
GPU computations:

* Compute text sequence lengths from the tokenizer's CPU mask before transferring
  the mask to CUDA. Reading lengths computed on the emulated device is invalid.
* Set UniPC's initial schedule index to zero for this complete T2V schedule.
  Discovering the index with a CUDA comparison/nonzero/item produced an
  out-of-range index (1838 in a 51-element schedule).
* Solve UniPC's tiny coefficient systems on the CPU, then transfer coefficients
  to the latent's device. Their inputs are schedule metadata. The previous GPU
  solve failed at `cusolverDnCreate` in the emulator.

There was a separate cuDNN dispatch failure at VAE decode (`GET was unable to
find an engine`). Both measured variants therefore select PyTorch's native CUDA
convolution backend with `--conv-backend native`. This is an explicit matched
backend choice, not a repair to GX's cuDNN implementation.

`test_boundary.py` checks exact CPU scheduler outputs for 4, 6, and 50 steps,
and identical token trimming for lengths 1, 4, and 8. It does not establish
bitwise equivalence between CPU and CUDA coefficient solves.

## Changes driven by the observed CPU work

[optimization.patch](optimization.patch) applies only to the boundary-fixed
baseline. The isolated source copies live under ignored `out/wan-gx/`.

| Observed repeated work | Application change |
| --- | --- |
| `model.to(device)` traverses the model every denoising step | Transfer once before the loop; retain generation/offload behavior |
| Rotary grid expansion/concatenation repeats for Q and K in every layer | Build grids once per transformer forward and reuse them |
| The fixed positive/negative prompt is embedded repeatedly | Cache text embeddings during one generation |
| Each layer projects identical cross-attention K/V every step | Cache per layer and prompt, clear on success or exception |
| Attention packs full-length K/V with slice-and-concatenate | Flatten directly when CPU lengths prove that all sequences are full; retain ragged fallback |
| VAE concatenates an increasingly long video after each chunk | Collect decoded chunks, then concatenate once |
| VAE recursively recounts an unchanged module tree | Cache convolution counts per instance |

Caches are scoped to this evaluation/no-grad application with fixed weights,
dtype/device and module topology during a generation. Context identity and
version are checked; source references prevent identity reuse. This is not a
general cache for training, concurrent forwards, or arbitrary model mutations.
Retaining per-layer K/V also increases live device memory during denoising;
GX does not establish its real-GPU peak-memory impact. Validate that tradeoff
alongside CUDA numerics before deploying the cache on hardware.

`test_optimizations.py` uses small real Wan modules on CPU to compare 12 nonzero
transformer outputs, context mutation, cache cleanup, VAE outputs for 1/3/5
chunks, and full/ragged/empty K/V packing. Transformer checks use CPU reference
attention; they do not validate FlashAttention CUDA kernel rounding. Performance
runs load the full official pretrained architecture and checkpoint.

## Measurement scope

[instrument.py](instrument.py) marks 25 real call regions and records only
host-owned shapes, lengths, schedule position, and module counts as PCVs.
A region's count is its own work; summing all regions avoids double-counting
nested calls. Counts include annotation bookkeeping attributed to enclosing
regions. Matching unmarked GX runs measure host elapsed time separately.

The final drperf boundary uses:

```
DRPERF_EXCLUDE_CUDA_MODULE=gx_cuda.so DRPERF_FOLLOW_THREADS=0
```

The selected module's instructions and synchronous callees beneath its CUDA
and GPU-library exports are excluded. Unmarked GX background workers are not
charged to the caller's regions. Explicitly marked threads remain measurable.
PyTorch/driver dispatch outside the excluded module is still included.
This measures marked caller-thread CPU work, not all host threads or GPU work.
The host already had a 1 GiB GX SysV arena, which GX reused despite the requested
8 GiB setting. Logs report soft-real allocations spilling to fake backing;
the application still completes, and no collectives are used here. This is a
material limitation of the emulator host-time comparison. We preserved the
pre-existing shared arena instead of deleting another experiment's IPC state.
Fresh environments may have different allocator overhead; the recorded timing
numbers describe this environment. GX allocation work is excluded from the
drperf CPU region counts by the call boundary.
The report records matching export/call counts and checks residual GX module
instructions. Earlier exploratory records used a narrower export filter and
are not mixed with the final measurements.

A complete run at one shape does **not** establish affine scaling. Many regions
have too few distinct PCV states to fit; `elements` alone fails badly for mixed
VAE convolutions, and schedule position alone fails for UniPC's changing paths.
These annotations are diagnostic starting points, not a claim that every
region passed an unexplained-cost threshold. The optimizations remove repeated
work identified by counts and source inspection; unexplained costs remain.

## Reproduction

Requires the GX installation described in `~/GX/NEX/usage.md`, its prepared
image, enough disk for approximately 17 GB of weights, and the built drperf
client. The experiment uses its own container, helper-managed via `run.mk`.
Adjust the host in `container.py` for a different machine. All runtime policy
is exported from [run.mk](run.mk); `container.py` stages it for `entry.sh`.
Do not run concurrent GX jobs sharing the host IPC namespace.
`entry.sh` takes an experiment-local lock to prevent overlapping these launches.

```
./build.sh
mkdir -p out/wan-gx
git clone https://github.com/Wan-Video/Wan2.1.git out/wan-gx/upstream
git -C out/wan-gx/upstream checkout 9737cba9c1c3c4d04b33fcad41c111989865d315
python3 examples/wan_gx/download.py
python3 examples/wan_gx/prepare.py
python3 examples/wan_gx/optimize.py
make -f examples/wan_gx/run.mk setup
make -f examples/wan_gx/run.mk command CMD='python3 -m pip install --no-deps -r /workspace/examples/wan_gx/dependencies.txt'
make -f examples/wan_gx/run.mk command CMD='OMP_NUM_THREADS=1 python3 /workspace/examples/wan_gx/test_boundary.py'
make -f examples/wan_gx/run.mk command CMD='OMP_NUM_THREADS=1 python3 /workspace/examples/wan_gx/test_optimizations.py'
```

Ensure `out/wan-gx/results` is writable by the container user (the experiment
used mode 1777 for this output directory). For each variant `baseline` or
`optimized`, choose a fresh output name:

```
make -f examples/wan_gx/run.mk command CMD='DRPERF_FOLLOW_THREADS=0 DRPERF_EXCLUDE_CUDA_MODULE=gx_cuda.so bash /workspace/examples/wan_gx/entry.sh python3 /workspace/examples/wan_gx/measure.py /workspace/out/wan-gx/results/baseline-final-profile python3 /workspace/examples/wan_gx/run_model.py --tree /workspace/out/wan-gx/baseline --mark --conv-backend native --output /workspace/out/wan-gx/results/baseline-final-profile.json'
python3 examples/wan_gx/analyze.py out/wan-gx/results/baseline-final-profile
```

For uninstrumented host timings, omit `measure.py` and `--mark`, and add
`--repeats 3`. Model loading is recorded separately. No timing simulator or
kernel prediction database participates. `baseline.sh` reproduces the original
unsupported application path; it is not the working baseline used for comparison.

Use `make -f examples/wan_gx/run.mk stop` when finished, or `resume` to reuse
the prepared container. Downloads verify the pinned Hugging Face revision
`37ec512624d61f7aa208f7ea8140a131f93afc9a` and LFS SHA256 digests. Model source,
weights and raw traces stay in ignored `out/`; patches, scripts and compact
measurement evidence are versioned here.
