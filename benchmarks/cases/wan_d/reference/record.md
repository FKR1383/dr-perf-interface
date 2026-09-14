### Wan case D. The text encoder's cost follows the padding, quadratically, and the prompt is free

`WanPipeline._get_t5_prompt_embeds` tokenises with `padding="max_length"` at
`max_sequence_length` (512) and runs the UMT5 encoder on the padded batch,
then slices each row to its real length and zero-pads again. Copy
`videogen/wan-t5`, markers `videogen/mark_t5.py`, driver `videogen/run_t5.py`
(encode-prompt only), grid real tokens {8, 32, 128, 480} x max length
{64, 128, 256, 512} x batch {1, 2}, one thread, every point repeated.

**Fit.** With `rtok` (summed real lengths), `ptok` (padded tokens),
`sq = batch*max_len^2/64` and `lsq = max_len^2/64`, on the points where the
prompt is shorter than the budget:

```
t5_enc      -1.2*rtok + 24,402.1*ptok + 20,723.2*sq + 4,625,186                       68.6% irregular   (three states)
t5_enc      24,980*ptok + 46,060.5*sq + 27,714.6*lsq + 6,807,980                      17.7%             (with lsq)
    ptok: mkl sgemm_kernel 10,497, mkl_vml sTanh 7,232        (projections, FFN)
    sq:   mkl sgemm_pst 17,664                                (attention, per padded token pair)
    lsq:  index_select_out_cpu 4,608, mkl_vml sLn 3,320       (the relative-position bias, rebuilt as (1, heads, L, L) in every layer)
```

The real prompt's coefficient is -1.2: it is free. Everything is paid per
padded token and per padded pair, and there is an unbatched L² term because
UMT5 materialises the position bias per layer. A second regime exists: a
prompt that exactly fills the budget is ~35% cheaper, since an all-ones
mask lets transformers skip the (B, 1, L, L) mask tensor.

**Surprise at production.** UMT5-XXL (24 layers, d_model 4096): 2,422 GMAC
per prompt padded to 512 against 148 at 32 real tokens, 4.84 versus 0.30
TFLOP, 16.3x (21.8x for 24 tokens), each layer materialising a 33.6 MB score
tensor and a 67.1 MB position bias where 0.13 and 0.26 MB would do.
Downstream the cross-attention's `kv_len` is exactly `max_sequence_length`:
`attn_qkv = 1,358*seq_len + 2,494.7*kv_len + 369,881` at 0.8% unexplained,
so 3,000 cross-attentions per video run over 512 keys, 154.6 TMAC, where
32 keys would be 9.7.

**Third beat, measured** (`videogen/patches/wan_t5_shortpad.patch`): encode
at the longest real length rounded up to a multiple of 8 (floor 16), then
zero-pad to `max_sequence_length` as before.

```
t5_embeds   25,688.3*ptok + 46,070.5*sq + 27,692*lsq + 6,565,689   ->   693.5*ptok + 34.8*sq - 27.7*lsq + 6,694,193
per call, batch 1, max_len 512:  8 real tokens 384.8M -> 8.07M (47.7x); 32 -> 8.46M (45.5x); 128 -> 17.3M (22.2x); 480 -> 124.5M (3.1x)
```

Prompt embeddings, negative embeddings, latents and decoded video are
bit-identical to pristine diffusers at ten encode points and three full
pipeline calls, worst absolute difference 0.0. The reason is checkable:
T5's position bias is relative and masked scores are shifted by
`finfo.min`, so real-token outputs do not depend on padding, and in float64
lengths 16 to 512 agree with length 8 to 1.55e-15 (a floor of 8 gives
4e-6 because BLAS switches kernel below M = 16).

**The half that cannot be done, and what it says.** Shortening `kv_len`
into the transformer is not behaviour-preserving: cross-attention is
called with `attention_mask=None` (`transformer_wan.py:569`), `to_k` and
`to_v` have biases, and `text_embedder(0)` is not zero, so every one of the
480 pad rows is a real key and removing them moves the output by 0.27 on
a scale of 2.3. The model was trained attending to its own padding;
15/16 of its cross-attention work is spent on it, and that cost is part of
the model now, not of the pipeline.

---

