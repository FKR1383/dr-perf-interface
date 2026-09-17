# Further Wan CPU optimization passes

Same official pretrained model, 832x480, 81 frames, 50 steps, CFG, seed,
precision policy, native convolution backend, and drperf binary/scope as the
[first comparison](RESULTS.md). Every profile completes the full schedule and
VAE decode, has zero GX module residue and passes collection validity checks.

| Variant | Marked CPU instructions, billions | Reduction vs baseline | Unmarked host seconds, 3 generations | Median seconds |
| --- | ---: | ---: | --- | ---: |
| Baseline | 23.632 | 0.00% | 10.731, 9.436, 9.460 | 9.460 |
| First pass | 18.945 | 19.84% | 9.271, 7.986, 8.017 | 8.017 |
| Metadata/layout pass | 15.443 | 34.65% | 7.484, 6.048, 6.064 | 6.064 |
| Dispatch pass | 14.387 | 39.12% | 6.758, 5.363, 5.406 | 5.406 |

## Changes and drperf feedback

1. **Attention metadata:** build cumulative lengths from CPU-owned lengths,
   reuse them across a generation, and keep the same variable-length
   FlashAttention entry point. CUDA-owned lengths retain the original path.
2. **Rotary work:** reuse grids for the generation and use a batched expression
   for a single unpadded sequence, avoiding empty concatenations and a stack.
   Multi-batch and padded inputs retain the general path.
3. **Patch embedding:** its temporal kernel is one, so apply the same weights
   as 2D convolutions over a batch of frames. Temporal kernels retain Conv3d.
   This changes the convolution implementation, not the model's mathematical
   operation; its measured benefit is specific to the native backend used here.
4. **Layout correction:** eliminating a concatenation initially increased layer
   norm cost because it removed a contiguous copy. drperf exposed the regression.
   Make the token input contiguous once, before the transformer blocks.
5. **Precision-scope dispatch:** remove three per-block autocast contexts around
   only add/multiply/chunk. The installed PyTorch CUDA dispatcher registers all
   three as autocast fallthrough; a test verifies that prerequisite. Scopes
   around operations that need float32 computation remain.
6. **RMSNorm:** use PyTorch's RMSNorm operation on float32 inputs, retaining the
   original output cast and subsequent weight multiplication.
7. **VAE:** avoid padding/copying when every requested padding amount is zero.

The patches are cumulative: [first pass](optimization.patch),
[metadata/layout pass](optimization-more.patch), then
[dispatch pass](optimization-dispatch.patch). Existing first-pass evidence is
preserved. All 25 marked region boundaries remain the same; marker bookkeeping
inside enclosing regions remains included.

| Region | First pass M instructions | Dispatch pass M instructions | Further reduction |
| --- | ---: | ---: | ---: |
| wan_flash_attention | 3727.69 | 2711.96 | 27.25% |
| wan_vae_conv | 2951.34 | 2950.66 | 0.02% |
| wan_block | 2845.42 | 2308.95 | 18.85% |
| wan_transformer | 2431.27 | 376.02 | 84.53% |
| wan_self_attention | 2180.08 | 2184.26 | -0.19% |
| wan_rope_apply | 1322.77 | 851.38 | 35.64% |
| wan_rms_norm | 1265.11 | 784.43 | 38.00% |
| wan_cross_attention | 1124.86 | 1123.04 | 0.16% |
| wan_layer_norm | 456.52 | 457.19 | -0.15% |
| wan_vae_residual | 202.09 | 202.18 | -0.04% |
| wan_scheduler | 94.82 | 95.33 | -0.53% |
| wan_generate | 50.70 | 50.62 | 0.15% |
| wan_t5_encoder | 48.38 | 48.31 | 0.16% |
| wan_model_to | 47.39 | 47.58 | -0.39% |
| wan_vae_resample | 37.09 | 37.14 | -0.13% |
| wan_vae_decoder | 33.24 | 33.39 | -0.46% |
| wan_t5_attention | 31.11 | 31.08 | 0.09% |
| wan_head | 27.19 | 25.84 | 4.96% |
| wan_t5_ffn | 19.20 | 19.09 | 0.53% |
| wan_time_embedding | 18.73 | 18.52 | 1.14% |
| wan_vae_attention | 13.28 | 13.26 | 0.19% |
| wan_tokenize | 10.66 | 10.66 | 0.02% |
| wan_vae_decode | 2.86 | 2.86 | -0.15% |
| wan_vae_clear_cache | 2.23 | 2.23 | -0.09% |
| wan_encode_text | 0.60 | 0.60 | -0.20% |

## Validation and limits

`test_more.py` includes the original nonzero transformer-output, context-mutation,
cache-cleanup and VAE checks. It adds exact rotary comparisons for padded/full
inputs, batches 1/2 and float32/bfloat16; grouped/strided/noncontiguous framewise
convolution checks and a temporal-kernel fallback; the actual attention-preparation
bodies with a CPU reference attention kernel; metadata mutation/cache cleanup;
and RMSNorm float32/bfloat16 comparisons. The convolution and RMSNorm checks use
explicit floating-point tolerances; additional CPU bfloat16 framewise convolution
cases match exactly. No GPU numerical-equivalence or generated
video-quality claim follows from CPU tests or GX, particularly for the new
convolution/RMSNorm implementations. Model-specific rewrites assume the fixed
inference configuration, without custom module hooks.

These remain emulator host timings: three consecutive generations per variant,
model loading excluded, no GPU timing simulation. The shared-arena spill and
native-convolution limitations from the first comparison still apply. Many
regions still have insufficient distinct PCV states for an affine fit; VAE and
scheduler fits still contain substantial unexplained work. The reductions are
measured CPU work, not a claim that every performance interface is accepted.

## Reproduce the extra passes

After preparing the first-pass `out/wan-gx/optimized` tree:

```
python3 examples/wan_gx/optimize_more.py
python3 examples/wan_gx/optimize_dispatch.py
make -f examples/wan_gx/run.mk resume
make -f examples/wan_gx/run.mk command CMD='OMP_NUM_THREADS=1 WAN_OPTIMIZED_TREE=optimized-dispatch python3 /workspace/examples/wan_gx/test_more.py'
```

Use the same [profiling and host-time commands](README.md#reproduction), with
`--tree /workspace/out/wan-gx/optimized-dispatch` and fresh output paths.
`report_more.py` validates and packages the completed measurements.
Compact evidence: [metadata/layout pass](evidence/optimized-more.json),
[dispatch pass](evidence/optimized-dispatch.json).

## Native GPU follow-up

A subsequent [real A100 PCIe 40GB run](NATIVE_RESULTS.md) of the same full
workload measured 218.88 s baseline versus 207.43 s candidate: 5.23% lower
generation latency in one pair, using cuDNN. Final latent relative L2 error is
3.15%; decoded pixel RMSE is 0.0379 on [-1, 1]. Both outputs are finite, but this
does not establish numerical or perceptual equivalence.
