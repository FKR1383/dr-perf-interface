# Native A100 kernel and transfer traces

All traces used the pinned PyTorch 2.11 CUDA 12.8 stack on A100 GPU1, a full
same-size warmup, and one measured request. Nsight captured CUDA activity only
from the measured generation through `cudaProfilerStart/Stop`; FastVideo's
markers ran in its GPU worker. Nsight adds host overhead, so the profiled
request wall times below are diagnostic and are not speedup measurements.

| Workload | GPU event span | Kernel and copy union | Gap inside span | Kernel durations | Host-to-device copy | Device-to-host copy |
|---|---:|---:|---:|---:|---:|---:|
| Inferix, host KV baseline | 41.296 s | 40.744 s (98.7%) | 0.552 s | 14.610 s | 211.44 GB, 16.157 s | 121.16 GB, 9.226 s |
| Inferix, GPU KV and no discarded whole decode | 12.501 s | 12.277 s (98.2%) | 0.224 s | 11.230 s | 61 KB, 0.006 s | 302 MB, 0.132 s |
| FastVideo, metadata mode before worker-output adaptation | 15.313 s | 15.003 s (98.0%) | 0.311 s | 14.632 s | 97.88 GB, 7.428 s | 485 MB, 0.071 s |

The union merges all recorded GPU kernel and memory-operation intervals;
kernel and copy durations can overlap and must not be added to estimate wall
time. The gap is the interval between the first and last recorded GPU events
that contains neither a recorded kernel nor a copy. It does not include time
before the first event or after the last event. CUDA API synchronization time
mostly waits for GPU work and is also not additive.

Inferix baseline had 3,300 `cudaStreamSynchronize` calls totaling 31.344 s of
host wait. With GPU KV and the redundant decode removed, host↔device traffic
fell from 332.60 GB to about 302 MB, while the GPU remained busy for nearly
its entire recorded event span. The combined variant's native output retained
the baseline shape `[1, 63, 480, 832, 3]` and exact mean/std. FastVideo's
native result retained `[1, 3, 81, 480, 832]` with mean `0.4022836685` and
std `0.2956195772`. FastVideo's large host-to-device traffic comes from a
separate default: `dit_layerwise_offload=True` even though the runner sets
`dit_cpu_offload=False`. The loader installs a hook that parks each DiT block's
weights in pinned CPU memory and prefetches them each forward. Copy sizes of
27,525,120 bytes × 2,100 and 4,718,592 bytes × 8,400 account for 97.44 GB of
the measured 97.88 GB; the counts equal 30 blocks × 70 forwards × one or four
parameter tensors. The runner has an opt-in `--resident-dit` switch for a
matched native/GX test. Because these copies overlap computation, the trace
alone does not predict the latency gain from removing them.

The fresh Inferix host-KV physical GPU profile contains all **327/327**
observed kernel signatures, **961** measured samples, and zero skipped
launches. The final FastVideo metadata GPU profile with worker-side CPU output
contains **396/396** observed signatures and **1,045** measured samples with
zero skipped launches. Its source, runtime environment, and output policy
match the native worker-output run. The Nsight trace in the table predates
this output adapter; its transfer totals characterize the model's layerwise
offload, not the final output boundary.
Both used `GX_PROFILE_WARMUP=0` after a full model warmup, so one-off signatures
were sampled. The FastVideo original-path database is separately complete at
409/409 signatures. Kernel databases are prediction inputs; Nsight traces
above describe actual native GPU work.

[Machine-readable trace summary](evidence/native-traces.json) names the raw
`.nsys-rep`, SQLite, stats, native reports, and GPU databases under
`out/causal-video/`. The uninstrumented latency and exact tensor validation
are documented in [NATIVE_RESULTS.md](NATIVE_RESULTS.md), with FastVideo's
native comparisons in [FASTVIDEO_NATIVE_RESULTS.md](FASTVIDEO_NATIVE_RESULTS.md).
