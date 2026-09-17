# FastVideo worker CPU instruction profile

The managed [81-frame drperf run](/home/ubuntu/GX/NEX/build/experiments/fastvideo-drperf81-early-1789611354395122031/result.json) passed after attaching DynamoRIO in the worker before warmup. The single measured generation completed with the matched metadata adaptation, worker CPU output transfer, FlashAttention, layerwise DiT offload, and worker Torch interop set to 1. The [validated summary](/home/ubuntu/drperf/out/causal-video/fastvideo-drperf81-early-summary.md) covers **8,632,102,827 exclusive host instructions** in application regions. The 18.86 s measured public call ran under DynamoRIO and is not a native latency estimate.

The worker's raw record has one observed PID and all required blocks, slots, and trigger files. It reports 1,551 excluded `gx_cuda.so` exports, zero GX-module instructions in every summarized region, and zero slot, counter, state, depth, trace, or unmatched-end overflows. The separate `fastvideo_attach_setup` region is excluded from application totals. The full [summary JSON](/home/ubuntu/drperf/out/causal-video/fastvideo-drperf81-early-summary.json) and [evidence manifest](evidence/fastvideo-drperf.json) retain the counts and artifact hashes.

| Exclusive worker region | Calls | Instructions | Share of marked total |
|---|---:|---:|---:|
| Transformer outside child markers | 35 | 4,995,926,811 | 57.88% |
| Causal denoising outside child markers | 1 | 1,066,177,352 | 12.35% |
| Cross attention | 1,050 | 694,798,419 | 8.05% |
| Self attention | 1,050 | 569,299,108 | 6.60% |
| Rotary application | 2,100 | 485,999,779 | 5.63% |
| VAE decoder | 21 | 360,225,832 | 4.17% |
| Pipeline outside child markers | 1 | 343,708,288 | 3.98% |
| RoPE table lookup | 35 | 568,769 | 0.0066% |

The measured RoPE lookup has exactly seven `start_frame` states, 0 through 18 in steps of 3; its fixed shape is `(3, 30, 52)` and head dimension is 128. The conditional fit is about **16,251 instructions per call** with zero fitted start-frame slope, a maximum 0.83% reconstruction error, and no unexplained fraction. The full five-PCV relation remains unidentifiable because shape and head dimension never vary. FastVideo already caches these tables in a 16-entry LRU, enough for the seven observed positions. Increasing cache capacity would not address this workload. The `fastvideo_rope` region measures GPU tensor-operation dispatch as host instructions; it does not show that RoPE is on the wall-time critical path.

The causal-denoising and pipeline exclusive regions contain CPU normal-random generation (`normal_fill_16`, `CPUGeneratorImpl::random`, and `normal_kernel` are their largest symbols). Changing that generation risks changing the seeded latent tensor and output, so this profile does not justify a semantic-preserving shortcut. Self-attention's observed context ranges from 4,680 to 32,760 tokens in seven states while per-call host instruction counts stay nearly flat. Its conditional context slope is about −0.0076 instructions/token at fixed 4,680 query tokens; it is not evidence that larger context reduces CPU work or end-to-end time. The instrumented `fastvideo_block` marker produced no recorded calls, so its unmarked host work remains in the transformer ancestor region.

No CPU optimization is recommended from this collection alone. The native Nsight analysis reports roughly 98% GPU busy time; host exclusive instruction share does not establish critical-path savings. The runner's 25.57 s GX trace cleanup grace happened after the measured interval and let the worker exit before FastVideo's five-second force-termination fallback. It changes trace completion, not the measured generation. The [final partial trace](FASTVIDEO_PARTIAL_RESULTS.md) is complete, but its launch audit still fails on 84 cuDNN predictions.
