# Official Wan on a real A100

This follow-up compares the boundary-fixed baseline with the final
`optimized-dispatch` candidate from [the GX experiment](MORE_RESULTS.md).
Both load the pinned official Wan2.1-T2V-1.3B checkpoint and execute real GPU
arithmetic, including UMT5-XXL, 50 denoising steps with classifier-free guidance,
and VAE decode. The generated tensor has shape `(3, 81, 480, 832)`.

## Results

| Variant | Full generation seconds | Peak allocated tensor memory, GiB |
| --- | ---: | ---: |
| Boundary-fixed baseline | 218.876 | 24.073 |
| Final optimized candidate | 207.425 | 24.054 |

The candidate saved **11.451 seconds (5.23% lower latency, 1.055x speedup)**
in this one pair. The 39.12% reduction in marked CPU instructions under GX
does not translate proportionally to GPU generation latency. This experiment
does not attribute the GPU speedup to individual changes; some optimizations
also eliminate GPU work or change kernel implementations.

Both outputs are finite, but **they are not numerically identical**:

| Tensor | RMSE | Relative L2 error | Maximum absolute difference | Cosine similarity |
| --- | ---: | ---: | ---: | ---: |
| Final denoised latent | 0.032277 | 3.152% | 1.171832 | 0.999503 |
| Decoded video, pixel range [-1, 1] | 0.037907 | 6.740% | 1.821623 | 0.997728 |

The candidate changes convolution and RMSNorm implementations as well as CPU
orchestration. This pair does not isolate which changes caused the differences,
or establish numerical/perceptual equivalence. The latency result is measured,
but the candidate is not yet a validated equivalent replacement. An ablation
or a separate quality assessment is needed to resolve that distinction.

Model loading took 50.791 / 60.336 seconds and warm-up took 4.368 / 4.254
seconds, baseline/candidate respectively; both are excluded from the table.
Source hashes exactly match the corresponding GX baseline and final candidate.
Compact records: [baseline](evidence/native-a100/baseline.json),
[candidate](evidence/native-a100/optimized.json),
[comparison](evidence/native-a100/comparison.json), and
[provenance](evidence/native-a100/provenance.json).

## Measurement

One full generation per variant, in separate processes, baseline first.
Each process performs an untimed 9-frame / 4-step generation first. The timer
starts before `generate()` and ends after CUDA synchronization. Model loading,
numerical checks, and saving tensors are outside the timer. File/video encoding
is not part of the measured pipeline.

Settings: 832x480, 81 frames, 50 UniPC steps, shift 5, guidance 5, seed 42,
prompt `A cat walks on the grass, realistic style`, and model offload disabled.
The configured model compute policy uses bfloat16, retaining upstream float32
operations. Both variants use cuDNN; the GX comparisons disabled cuDNN because
of an emulator dispatch failure. This checks the normal native convolution
backend, so the GX CPU percentage is not an expected GPU latency percentage.

The reference includes the common CPU-owned metadata repairs in
[metadata.patch](metadata.patch). It is not pristine upstream. The candidate
additionally includes all three optimization patches. No DynamoRIO, drperf
instrumentation, GX interception, or timing simulator runs during these timings.

## Environment and reproduction

Physical GPU 1 on the `A100` host: A100 PCIe 40GB. Only this GPU is exposed to
the experiment container, where CUDA numbers it as device 0. Physical GPU 0
runs a separate vLLM workload and is untouched. The host is shared; the
GPU is dedicated to this experiment during its run. One timing pair cannot
establish variability or a statistically reliable small speedup.

The host CPU is an AMD EPYC 9554. The container has an 8-CPU quota and 64 GiB
RAM limit; Torch/OpenMP/MKL/OpenBLAS use one thread. Image `gx-kimi-k3:latest`,
ID `sha256:430f87a5b3b6689c7142b33ce7fa355d1107cd95c3d81f0ac871e271d27508d9`.
Torch is 2.11.0+cu128, matching the GX experiment. FlashAttention
2.8.3+cu12torch2.11cxx11abiTRUE is copied from the retained GX container into
`/workspace/deps`, preserving the tested build. The additional packages in
[dependencies.txt](dependencies.txt) are installed with `--no-deps`.

The image's system and pip cuDNN libraries initially conflicted during the
optional PEFT import. The failed attempt did not reach generation. Setting
`LD_LIBRARY_PATH` to Torch's pip cuDNN directory fixed both the import and a
real convolution/FlashAttention preflight. Both timed variants use this path.

Prepare the source trees and checkpoint using [README.md](README.md), including
the further optimization passes. Stage `out/wan-gx/baseline/` as remote
`baseline/`, `out/wan-gx/optimized-dispatch/` as `optimized/`, the checkpoint as
`checkpoint/`, and `native.py`, `compare_native.py`, and `dependencies.txt` in
the remote workspace. Create a writable `results/` and a `setup/` directory.
Adjust `WAN_NATIVE_HOST` and `WAN_NATIVE_WORKSPACE` if needed; the host inventory
in `native_container.py` selects physical GPU 1.

```
make -f examples/wan_gx/native.mk setup
make -f examples/wan_gx/native.mk command CMD='python3 -m pip install --no-deps -r /workspace/dependencies.txt'
make -f examples/wan_gx/native.mk run VARIANT=baseline
make -f examples/wan_gx/native.mk run VARIANT=optimized
make -f examples/wan_gx/native.mk command CMD='OMP_NUM_THREADS=1 python3 /workspace/compare_native.py /workspace/results/baseline /workspace/results/optimized --output /workspace/results/comparison.json'
make -f examples/wan_gx/native.mk stop
```

Use fresh output directories for another pair: the runner refuses to overwrite
an existing variant directory. Raw tensors and logs remain in ignored storage.
The comparison checks matching workload/environment metadata and reports latent
and decoded-pixel differences. These metrics do not measure perceptual quality.
