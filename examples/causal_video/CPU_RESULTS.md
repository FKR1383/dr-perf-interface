# Inferix RoPE frequency cache: CPU result

The opt-in RoPE frequency cache reduced measured host instructions, but did not improve native A100 request latency. For the full 21-latent-frame pretrained request, five warmed native runs had a **12.688059104 s** baseline median and a **12.694004179 s** cache median. The 0.005945075 s difference (0.047%) is smaller than the run-to-run spread and is not evidence of a speedup. Both variants used GPU-resident KV, the same model and assets, a full same-size warmup, and the same generation harness.

| Full native request | Baseline | RoPE cache | Candidate change |
| --- | ---: | ---: | ---: |
| Five request times, s | 12.5533, 12.6347, 12.6881, 12.7269, 12.7623 | 12.5696, 12.6390, 12.6940, 12.7420, 12.7751 | median +0.0059 s |
| Peak GPU allocated | 30,990,772,224 B | 31,024,916,480 B | +34,144,256 B (+32.56 MiB) |
| Peak GPU reserved | 32,260,489,216 B | 33,608,957,952 B | +1,348,468,736 B (+1,286 MiB) |

The candidate report records seven live frequency grids using 33,546,240 B, with 12,593 hits, seven misses, and no evictions over warmup and five requests. The allocated-memory increase is close to the live cache size. The larger reserved-memory increase is a caching-allocator outcome observed in this run; these measurements do not identify its cause.

A separate matched GX drperf comparison counted **5,227,639,115** versus **4,955,856,063** exclusive host instructions across marked regions, a reduction of **271,783,052 (5.20%)**. The `inferix_causal_rope` region retained 2,100 calls and fell from **752,732,316** to **498,905,046** exclusive instructions, a reduction of **253,827,270 (33.72%)**. Both collections report no validity errors and exclude instructions inside `gx_cuda.so`. These counts show less host work at this marker; they do not measure GPU execution or predict native request latency. The native A100 and GX drperf hosts also use different CPUs.

Exact semantic checks passed at zero tolerance. The full request saved an identical `[1, 63, 480, 832, 3]` video tensor. A separate warmup and two six-latent-frame segments matched callbacks, segment videos, and final latents exactly, with VAE caches empty on both sides. The validation-copy runs were not used for timing.

The cache remains opt-in via `INFERIX_ROPE_FREQ_CACHE=1`. It is suitable as a tested CPU-work reduction, but the native result does not justify enabling it for latency. [Compact evidence](evidence/inferix-cpuopt.json) records the source reports, exact metrics, and comparison results; [implementation details](cpu_patches/README.md) describe the patch and cache key.
