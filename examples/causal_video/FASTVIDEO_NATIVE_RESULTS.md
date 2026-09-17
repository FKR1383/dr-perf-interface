# FastVideo native A100 results

The final matched FastVideo workload is SelfForcing T2V-1.3B, one 81-frame
480×832 request at four denoising steps on A100 GPU1. Both native variants
use the pinned `FastVideo-metadata` source, worker-side CPU output adaptation,
FlashAttention, PyTorch 2.11, cuDNN 91900, and one full warmup before three
timed public `generate_video` calls. OMP, MKL, and OpenBLAS threads are 1;
worker Torch interop threads are explicitly 1. The source preparer and opt-in
output adaptation are documented in [fastvideo_patches/README.md](fastvideo_patches/README.md).

| DiT weight policy | Public-call times (s) | Median (s) | Peak GPU allocated | Peak GPU reserved |
|---|---|---:|---:|---:|
| Default layerwise CPU offload | 15.3089, 15.4242, 15.4518 | 15.4242 | 20.405 GB | 29.645 GB |
| Resident DiT (`--resident-dit`) | 15.2414, 15.3596, 15.3859 | 15.3596 | 23.102 GB | 30.746 GB |

The resident median was 0.0646 s (0.42%) lower, less than the spread across
each set of three calls. It used 2.697 GB more peak allocated and 1.101 GB
more peak reserved GPU memory. These measurements do not show a compelling
end-to-end gain from disabling layerwise offload for this workload. The
offload policy is independent of `dit_cpu_offload=False`: FastVideo defaults
`dit_layerwise_offload=True`. The [Nsight trace](NATIVE_TRACE.md) attributes
97.44 GB of 97.88 GB host-to-device traffic to repeated DiT block weight
prefetches, but most copy time overlaps kernel execution.

Both variants produced finite `[1, 3, 81, 480, 832]` float32 samples with
mean 0.4022836685 and standard deviation 0.2956195772. Their saved fp16
tensor files have the same SHA256,
`642f5f2a44e2c3a318b66f2c26dab5477c198c25ce809740ced2808ff6125410`,
also seen in a current-environment run of the original FastVideo source and
the adapted native run. This establishes equality of the serialized fp16
samples. It does not establish bitwise equality of full fp32 tensors or
assembled frame grids. An older environment yielded a different fp16 hash;
the original-source Nsight control reproduced the newer hash, so the
diagnostic assert adaptation did not cause that difference. The old and new
environments changed cuDNN library path, backend selection variables, and
thread controls together; no single cause has been isolated.

The final physical GPU profile covers all **396/396** observed signatures
with **1,045** measured samples and zero skipped launches. It uses the same
source, output policy, explicit runtime settings, and worker interop=1 as the
native comparison. Its roughly 16-second profiled call includes profiler
overhead and is not a native latency result. The worker report records hashes
of mapped cuDNN libraries after warmup for native/GX identity checks. The GX
worker timeline includes GPU uint8 quantization and both output transfers;
it does not account for parent-side frame-grid CPU work and thus is not the
whole public-call duration.

Raw native reports and GPU database are named in
[evidence/fastvideo-native.json](evidence/fastvideo-native.json). The runner
used for the three-repeat native timings differs from the final GPU-profile
runner only by a later GX-trace-only shutdown-grace branch, inactive on the
native and GPU-profile paths.
