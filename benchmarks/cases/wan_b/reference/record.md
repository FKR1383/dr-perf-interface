### Wan case B. The paths the first pass did not mark: rotary application, callbacks, the VAE posterior, tiling

24 more regions (`videogen/mark_more.py`, copy `videogen/wan-more`), seven grids
of 90 points in all (`out/videogen_more_*`), driver `videogen/run_more.py`
with modes for text-to-video, VAE encode, tiled decode, and a real tiny
`UMT5EncoderModel` so prompt encoding is measured too.

```
attn_rope      = 5,764.3*seq_len + 0*heads + 0*batch + 320,506.1        0.4% irregular
    per token: c10::function_ref callback 3,064, serial_for_each 1,264, callback 896, DimCounter::increment 352
attn_qkv       = 1,622.5*seq_len + 3,023.2*kv_len + 0*heads + 405,870.8  1.4%
attn_sdpa      = 157*seq_len + 1.9*kv_len + 0*heads + 97,709.3          98.6%
attn_out       = 1,403.2*seq_len + 0*heads + 0*batch + 129,319.2         0.0%
callback_step  = 14,019.5*ninputs + 0.00755*numel + 10,872.6             5.4%
    per name: PyDict_Contains 2,436, PyDict_SetItem 2,044, PyDict_Update 1,850, PyObject_SetItem 1,469
dgd_init       = 0*chans + 14.2*numel + 114,569.1                        2.7%   (mkl_vml_sExp 13.6 of the 14.2)
blend_v_r      = 114,147.7*extent + 64.4*frames + 0*width + 4,934        5.3%
blend_h_r      = 112,494.6*extent + 64.4*frames + 0*height + 5,068.2    15.4%
pp_stack       = 0*batch - 8*frames + 0*height + 26,205.5               94.5%
prompt_clean_r = 10,931.8*batch + 439.7*chars + 101,552.5               93.7%
```

**Rotary application is the most expensive host phase of attention.**
`apply_rotary_emb` (`transformer_wan.py:104-118`) costs 5,764 per token at
0.4% unexplained, 3.6x the QKV projections and 4.1x the output projection,
and not one of its top functions is arithmetic: the stride-2 interleaved
layout puts TensorIterator on its scalar `DimCounter` path, with two
full-size temporaries and two strided copies, 45 instructions per rotated
element. The tables it reads are half duplicates: `get_1d_rotary_pos_embed`
with `repeat_interleave_real=True` emits two 16.8 MB tables at production of
which `apply_rotary_emb` uses `cos[..., 0::2]` and `sin[..., 1::2]` only
(`even == odd` verified).

**`locals()` per callback name per step.** `pipeline_wan.py:640` builds the
callback's inputs by calling `locals()` for each requested name, 14,019
instructions of dictionary machinery per name; the default is three names,
42k per step to read three variables already in scope.

**The VAE posterior computes what it discards.** `DiagonalGaussianDistribution.__init__`
(`vae.py:693-694`) evaluates `std` and `var` eagerly, an `exp` over the whole
latent, 14.2 per element with `mkl_vml_sExp` 13.6 of it; `mode()`, which is
what the pipeline uses, reads neither. 9.3 ms per encode at production.

**The blend loops, and why not to fix them.** `blend_v`/`blend_h`
(`autoencoder_kl_wan.py:1268-1281`) cost 114k per row regardless of the row's
size, pure descriptor and bound-method allocation, 161M per tiled decode at
production. The formula also says the vectorised form would lose: at 81
frames a row holds 62k elements, Python is ~27% of it, and the one-shot
version allocates a 15.9 MB temporary and measures slower (21.9 to 27.4 ms).
It dominates only for tiny tiles.

**Two negatives worth having.** `pp_stack` is the one serial pass over the
whole video (0.35-0.48 per element, single-threaded, ~34M on one core at
production) and is what `pt_to_numpy`'s deferred transpose lands on;
`prompt_clean`'s residue (ftfy) is content-dependent and genuinely
undeclarable, with 68 instructions per character in `_PyErr_CheckSignals`
from its codec probing.

**Third beat, measured** (`videogen/patches/wan_more_{rope_apply,dgd_lazy,cb_locals}.patch`,
`out/videogen_fix2_*`; latents, video, 55 digests of rotary outputs,
posterior statistics, tiled configs and post-processing all identical):

```
dgd_init        14.2*numel + 114,569.1      2.7%   ->   0.349*numel + 70,030      1.8%     (40x on the slope; 9.31 -> 0.10 ms per production encode)
callback_step   14,019.5*ninputs + 10,872.6 5.4%   ->   425*ninputs + 26,940      0.0%     (33x per name)
attn_rope       5,764.3*seq_len + 320,506   0.4%   ->   5,675.3*seq_len + 323,964 0.4%     (-1.5% instructions; 210.9 -> 157.7 ms per q or k at production, -25% wall)
```

The rotary line is the honest caveat of this whole document in one row:
the fix removes memory traffic and temporaries, not instructions, so the
instruction cost function reports -1.5% where the clock reports -25%.
Instructions are not time, and this is the place it mattered.

The client key-merge bug bit again: the pre-existing one-state
`set_timesteps(steps=2)` merged into `encode_prompt(batch=2)`; every new
region here carries a constant tag state to keep signatures unique.

---

