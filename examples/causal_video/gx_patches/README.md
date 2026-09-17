# Inferix CUDA 13 export-table logger

`cuda13_logging.patch` applies to the isolated GX runtime source at `out/causal-video/gx-runtime/src/sims/gpu/emu/driver.c`. It fills slot 1 of GX's CUDA 13 private export table with a variadic error logger. cuDNN calls this slot while checking candidate kernel launch grids. With the slot null, the first report jumps to address zero and segfaults.

GDB evidence: `out/causal-video/debug-inferix-newdb-gdb3.log` shows `RIP=0` called from `libcudnn_engines_precompiled.so.9` at `cudnnBackendExecute`, with `rax` pointing to `cuda13_requirements_interface` and slot 1 null. The attempted call has domain `CUDA`, severity `0`, and format `Grid Dimensions (%u,%u,%u) include one or more zero values. All dimensions must be nonzero`. The old runtime SHA-256 was `5a6dba140f9af85b04f4ba95c8b6fdd1cbcb7b6e1d81c3b5739cbe99bcf4766a`.

The logger-only overlay driver source SHA-256 is `b77d540a14eaff898355aa865ed7347835cf34c2587d9bb0b804401b3aaf53a2`; its first built `gx_cuda.so` SHA-256 was `c9cc6e08a7b327dbe3d9d39fda53db50a5420140cd902bfce5915cea866404bc`. The current isolated overlay also includes `kernel_attributes.patch` below. Rebuild that overlay on this non-CUDA host with an explicit local CUDA-header repository override and SQLite link path:

```sh
cd /home/ubuntu/drperf/out/causal-video/gx-runtime
bazel build \
  --override_repository=cuda_headers=/home/ubuntu/drperf/out/wan-timing/cuda-headers \
  --linkopt=-L/home/ubuntu/drperf/out/wan-timing/build-libs \
  //src/sims/gpu:gx_cuda.so
```

Managed verification: the matched-metadata DB 3-frame emulation passed in GX run `1789607160519949783`. The 21-frame warmup plus 21-frame CPU-profile run passed in `1789607376494343549`; its CUDA occupancy summary was 8,400 hits and zero misses, and its model report had shape `[1,63,480,832,3]`. The logger emitted 26 oversized-grid messages during the full run, so cuDNN exercised the callback and continued. The CPU profile, model report, GX log, and native/GX measured launch inventory audit are under `out/causal-video/inferix-cpu21/`. That audit found 97,779 measured GX launches, equal to native non-cuBLAS wrapper launches, with 97,611 matching at exact kernel signature. The 168 remaining launches use different cuDNN transform/convolution signatures and require review against the refreshed native profile before claiming timing fidelity.

## Native duration represented by the unmatched cuDNN launches

Using the refreshed native GPU DB and the exact native/GX signature count differences, the 168 native launches replaced by GX variants represent **110,204,844 ns (0.1102 s)** of estimated summed native kernel duration. The estimator multiplies each signature's unmatched native count by its median usable isolated-gate GPU sample duration. The equivalent estimate over all **97,779 non-cuBLAS-wrapper native launches** is **10,359,623,849 ns**, making the unmatched share **1.064% of native summed kernel duration**, versus 0.172% of launch count. It is **3.09%** of the 3.5653 s estimate for cuDNN-named kernels. The largest terms are 34 BF16 indexed-convolution launches at 1.932288 ms median each (65.70 ms) and 34 BF16 NCHW-to-NHWC transforms at 0.931840 ms median each (31.68 ms).

Each of the seven unmatched native signatures has three usable samples. This is a sample-median estimate, not measured end-to-end time or a confidence interval. Summed kernel durations can overlap and exclude copies, synchronization, host work, and plan-selection overhead. GX runs different kernels for those calls, so native duration does not estimate GX duration or prediction error. [Detailed calculation](../../../out/causal-video/inferix-partial-cudnn-time-coverage.json) records each signature, sample count, median, and weighted duration.

## Kernel-attribute safety patch

`kernel_attributes.patch` repairs `cuKernelGetAttribute` and `cuKernelSetAttribute`, which previously returned success without supplying or changing the requested attribute. It validates GX's registered CUkernel handle and delegates to the existing CUfunction attribute implementation. `GX_CUDA_KERNEL_ATTR_DEBUG=1` logs the first 128 attribute calls and values for a bounded diagnostic run. The patch builds in the isolated overlay (`gx_cuda.so` SHA-256 `a0f6d3ff5ef819a7674b0dd5deac698da1f87f23b1b31836e84fb86b8078dfee`). That implementation still has generic function-attribute defaults; the patch alone does not establish cuDNN plan parity or explain the grid warnings.

The subsequent full diagnostic run still emitted invalid-grid warnings and logged no kernel-attribute calls, so this repair was not on the observed warning path. `cudnn_output_probe.patch` is an unapplied, logging-only follow-up for selected output APIs and invalid grids reaching `cuLaunchKernelEx`; it is not part of the built library. The build command above assumes the already prepared isolated GX overlay and its dependencies. These patches alone do not recreate that complete overlay from a clean GX checkout.
