## Video generation: Wan 2.1 in diffusers, the host side

The pipeline for the most widely used open video model, `WanPipeline` in
diffusers (source checkout `c5469b7`), built from a tiny randomly
initialised config so a full call runs on CPU in 0.3-5 s: a 2-layer
transformer of 64 hidden, a `AutoencoderKLWan` with base dim 8, the default
flow-match Euler scheduler, precomputed prompt embeddings. 51 runs over a
grid of frames {5, 9, 17} x steps {4, 6, 8} x resolution {128, 192, 256} and
a batch/text grid (`videogen/run_tiny.py`, markers `videogen/mark_wan.py`,
runs `out/videogen_tiny`, `out/videogen_batch`, `out/videogen_sweep`). There
is no GPU here, so the matmul and attention kernels are counted too; they
land almost entirely in the irregular term (`mkl_blas_def_sgemm_kernel`,
`cpu_flash_attention`, `somatcopy`), and the affine coefficients and
constants are the host orchestration. Read those.

```
wan_call            = 4,537,754.2*num_frames + 3,075.2*height + 0*width + 11,431,003.3*steps + 27,397,965.9   98.7% irregular
denoise_step        = 0*batch + 51,290.3*frames + 2,457.9*height + 0*width + 12,257,258.1                      93.0%
transformer_forward = 0*batch + 55,729.1*frames + 27,874.9*seq_len + 6,111,945                                 76.7%
block               = 0*batch + 12,424.7*seq_len + 0*text_len + 2,172,643.1                                    79.5%
attn                = 0*batch + 421.6*seq_len + 0*heads + 448.2*kv_len + 423,543.8                             95.7%
rope                = 29.9*frames + 0*height + 0*width + 312,303.4                                             35.2%
cfg                 = 59,421.1*frames + 268.1*height + 0*width + 437.5*numel + 6,327,426.6                     76.4%
sched_step          = 0*batch + 105.8*frames + 1.1*numel + 63,619.2                                             0.1%
set_timesteps       = 105*steps + 201,993.1                                                                     0.1%
vae_decode_frames   = 0*batch + 8,219,409.3*frames + 9,365.7*height + 447,552.7                                99.7%
cond_embed          = 3,855.4*batch - 37*text_len + 617,350.4                                                  55.9%
```

**Surprise 1: the rotary embedding is recomputed on every forward.**
`WanRotaryPosEmbed.forward` (`transformer_wan.py:395`, called at `:668`)
depends only on `hidden_states.shape`, and runs on every transformer call:
312k fixed instructions plus ~400k irregular per call, twice per step with
CFG. At 81 frames and 480x832 that is 33.5 MB of identical cos and sin
rebuilt 100 times per 50-step call, 3.3 GB of the same tensor.

**Surprise 2: the prompt is re-projected every step.**
`self.text_embedder(encoder_hidden_states)` at `transformer_wan.py:347` runs
on every forward and every CFG branch on an input that does not change
within a call: `cond_embed` is 617k fixed here; for the 1.3B model about
8.9 GFLOP per forward, ~0.9 TFLOP per video, for one projection.

**Surprise 3: the VAE decode rebuilds the video per frame.**
`autoencoder_kl_wan.py:1197-1205` decodes latent frame by latent frame and
does `out = torch.cat([out, out_], 2)` each iteration, so the bytes copied
are quadratic in frames. Measured per latent frame: 568.5M at 2, 666.7M at
3, 735.1M at 5 (+29%), with `somatcopy` the top irregular symbol. At 21
latent frames (81 output frames) the penalty is roughly ten times larger.
`_encode` at `:1154` has the same shape.

**The fixed per-step dispatch.** `denoise_step` 12.26M per step, `block`
2.17M per layer, `attn` 424k per attention, all shape-independent
interpreter and dispatch (`_PyEval_EvalFrameDefault`, `PyDict_Contains`,
`OperatorEntry::lookup`). At 30 layers that is ~91M instructions of host
time per forward before any kernel, 100 forwards per call. Smaller items:
a full-size `torch.ones` mask per call at `pipeline_wan.py:574` used only by
Wan 2.2's `expand_timesteps`, and `hidden_states.contiguous()` per forward
at `:674`.

**The fit beat, owed and now paid** (`videogen/mark_fit.py`, `videogen/wan-fit`
rebuilt from the pristine checkout, `out/videogen_fit`, same 27-point grid).
Declaring the product the attention kernel scales with:

```
attn                 421.6*seq_len + 448.2*kv_len + 423,543.8                          95.7%
                 ->  1,150.4*seq_len + 1,244.3*kv_len + 39.9*sq + 0*batch + 1,986,510.3   37.1%   (sq = seq_len*kv_len)
block                12,424.7*seq_len + 2,172,643.1                                     79.5%
                 ->  27,970.5*seq_len + 40.1*sq + 2,374,257.6                            23.3%
transformer_forward  55,729.1*frames + 27,874.9*seq_len + 6,111,945                      76.7%
                 ->  57,926.8*seq_len + 80.2*sq + 6,513,670.2                            24.6%
```

The square lands where it should: `mkl_blas_def_sgemm_kernel_0_zen` 33.4,
`sgemm_scopy` 5.3, `sgemm_mscale` 1.4 per element of the attention matrix
in `attn` and `block`, and exactly twice that in `transformer_forward`, two
layers. What is left in all three is one thing, `at::native::cpu_flash_attention`
(2.6M + 1.6M per attention call), a fused kernel whose block count is not
affine in `seq_len*kv_len` because of its tiling and tail handling; no
product state reaches it. At production those kernels are GPU work; what
transfers is the constants and the linear host terms: `attn` 1.99M,
`block` 2.37M + 28k per token, `transformer_forward` 6.51M + 58k per token,
`denoise_step` 12.9M, per call.

**A derive bug this exposed.** `wan_call` got worse, 98.7% to 99.7%, and its
`11,431,003*steps` term, the largest host term at production, became
`0*steps` with the note "linear function of the earlier states". It is
not. `lib/derive.py:_solve` marks a column dependent when its pivot falls
below `1e-9 * max|A|`; with `sq` around 6.4e12 in the basis the threshold
is ~6.4e3 while the `steps` column's contribution is 72, so `steps` is
dropped unconditionally, and the same mechanism removed `frames` from
`transformer_forward` and `steps` from `denoise_step`. Declaring a large
computed state next to a small one costs the small one. The fix is to
scale columns before solving; the workaround is to declare the square in
units that keep the magnitudes comparable. Done (`mark_fit2.py`,
`out/videogen_fit2`, `sq_k = seq_len*kv_len // 1024`, `area_k = h*w // 64`):

```
wan_call       0*steps + 2,197,527*frames + 0.14*sq + 10*area + 8,750,015                    99.7%
           ->  11,838,056.2*steps + 4,712,994*frames + 614.7*sq_k + 797.5*area_k + 29,880,238.2   98.7%
transformer_forward  ... + 0*frames + 6,513,670   ->   61,041.4*seq_len + 79,726.8*sq_k + 55,843.9*frames + 6,747,196.1   23.4%
attn per-sq_k attribution: sgemm_kernel 34,232.1, sgemm_scopy 5,390.1, sgemm_mscale 1,407.6  (33.43, 5.26, 1.37 per element: unchanged)
```

`steps` is back at 11.84M per step against 11.43M in the unsquared
baseline, attributed to `_PyEval_EvalFrameDefault` 1.24M and
`PyDict_Contains` 400k, host dispatch as claimed; `frames` is back in
`transformer_forward` at 55.8k against 55.7k. Replaying `_solve`'s pivot
test on the state points reproduces every drop in `videogen_fit` and none
in `videogen_fit2`.


**Relations** (exact at every trigger): `attn.seq_len = last(block.seq_len) = last(transformer_forward.seq_len)`,
`rope.{frames,height,width} = last(denoise_step.*)`, `vae_decode.frames = last(denoise_step.frames)`,
`count(vae_decode_chunk) = cum(vae_decode.frames)` (one decoder pass per latent frame),
`set_timesteps.steps = last(wan_call.steps)`.

**Third beat, measured** (`videogen/patches/wan_{rope,text_embed,vae_cat,misc}.patch`,
`out/videogen_fix`, `out/videogen_fix_batch`; latents and decoded video
byte-identical by SHA-256 at five grid points, VAE encode and decode
separately identical at 1, 5, 9, 17 frames):

```
rope         cost(frames, height, width) = 29.9*frames + 0*height + 0*width + 312,303.4   35.2%   ->   0.5*frames + 44,711.8    22.9%
             mean per call 482,987 -> 58,612 (-87.9%); first call 782k, every cached call 13,679
cond_embed   cost(batch, text_len) = 3,855.4*batch - 37*text_len + 617,350.4   55.9%   ->   3,943*batch + 0.07*text_len + 513,647.5   34.2%
             mean per call 780,728 -> 564,337 (-27.7%); the residue is the timestep embedding, which does change per step
wan_call     4,537,754*num_frames + 11,431,003*steps + 27,397,966   ->   4,501,651*num_frames + 10,750,513*steps + 27,537,440
```

The rotary cache keys on (frames, height, width, device, dtype) and is
invalidated on shape change; the prompt projection is memoised on tensor
identity and version, bypassed under autograd, at most four entries. At
81 frames, 480x832, 50 steps with CFG on the 1.3B model these are about
0.72 s and 1.92 s of host time per call on this machine, and both also
remove GPU work: two 32,760 x 128 tables per forward, and ~870 GFLOP of
projection per video.

**And a correction the third beat forced.** The rising per-latent-frame
VAE cost was not the `torch.cat`. Per latent frame at 256 wide, baseline /
cat fix only / all fixes: 573.5M / 560.8M / 560.6M at 2 frames, 666.6M /
661.4M / 657.9M at 3, 738.0M / 737.7M / 735.0M at 5. It still rises,
because chunk 0 (`first_chunk=True`) emits one output frame at ~265M
while every later chunk emits four at ~855M, and `(265 + (F-1)*855)/F`
reproduces 562, 662 and 741M exactly. The cat is real but ~1% at this
tiny VAE (base dim 8 against 96 in production), where a chunk does about
1/144 of the convolution work per output pixel. At production width the
list-then-cat measures 927.5 ms to 92.3 ms for the concatenation itself
(4.12 GB of copies to 388 MB), so the fix stands, on different evidence
than the surprise cited. `.contiguous()` at `transformer_wan.py:674` is
not a no-op either: after `flatten(2).transpose(1, 2)` the strides are
`(81920, 1, 1280)`, so a guard would save nothing, and none was applied.


---

