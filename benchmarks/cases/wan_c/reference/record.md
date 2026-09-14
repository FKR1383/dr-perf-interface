### Wan case C. The per-step host constant, decomposed: cross-attention re-projects the prompt 3,000 times

`denoise_step` carries a ~11.5M-13M constant per step that no declared state
touches. Fifty-five temporary probes (`videogen/mark_tax_probe.py`, one state
each, unique multiplier bands so the client cannot merge them, verified over
27 runs x 76 regions with exact trigger counts) split it into its sub-steps,
then were removed. The step scaffolding is 1.3% of it; the rest is the two
transformer calls, and inside those, per layer:

```
sub-step (per layer)     before       after            sub-step (per forward)   before     after
bl_attn1 (self-attn)   1,129,822   1,059,251           tf_cond (timestep+text)   632,627   416,146
bl_attn2 (cross-attn)  1,013,395     763,454           tf_shift (modulation)      51,627    41,824
   ax_qkv                378,712     137,932           tf_rope                   104,682   105,452
bl_ffn                   214,604     221,311           tf_patch                  115,045   114,522
bl_norm1/3               212,394     192,827           at_rope (per self-attn)   320,122   279,012
bl_norm2                  78,346      60,556           at_out                    118,046    87,985
bl_mod (6-way chunk)      49,040      40,774           tf_normout                110,746    99,314
```

Attribution throughout is `_PyEval_EvalFrameDefault`, `PyDict_Contains`,
`_PyObject_GenericGetAttrWithDict` (the `nn.Module.__getattr__` walk),
`_int_malloc/_int_free`, `at::native::slice` in the modulation chunk, and
in `ax_qkv` alone `mkl_blas_def_sgemm_kernel_0_zen` 130,563 of 378,712.

**The surprise.** Cross-attention's `to_k` and `to_v` project
`encoder_hidden_states`, which is fixed for the whole call, on every block
of every forward: 30 layers x 100 forwards = 3,000 projections per video
where 60 (one per layer per CFG branch) would do. The rest of the list is
the same shape at smaller scale: the timestep embedding and the
`scale_shift_table + temb` modulation are recomputed for the second CFG
branch although the pipeline passes it the same `timestep` tensor;
`FP32LayerNorm` re-upcasts an input and weights that are already fp32;
`to_out[1]` is `Dropout(p=0)`, a module call and an ATen dispatch for the
identity; the two rotary half-tables are sliced twice per attention and
`out.type_as` after `empty_like` is always the identity.

**Third beat, measured** (`videogen/patches/wan_tax.patch`, `out/videogen_tax`;
latents and video identical at all five equivalence points, e.g. latents
`c64589693a19156c…`, video `5167edcaa39e7205…`), all memoised on tensor
identity plus `_version`, bypassed under autograd, or provably identity:

```
ax_qkv (cross-attn K/V)   378,712 -> 137,932   (-63.6%)
tf_cond                   632,627 -> 416,146   (-34.2%)
bl_norm2                   78,346 ->  60,556   (-22.7%)
at_out                    118,046 ->  87,985   (-25.5%)
bl_mod / tf_shift          49,040 ->  40,774 / 51,627 -> 41,824
at_rope                   320,122 -> 279,012   (-12.8%)
block                12,424.5*seq_len + 2,177,148.7   ->   12,424*seq_len + 1,967,858.2
transformer_forward  54,619.5*frames + 27,605*seq_len + 5,678,082   ->   54,911*frames + 27,604.2*seq_len + 5,005,886.4
wan_call             ... + 10,750,513.4*steps + 27,537,440   ->   ... + 9,502,853.1*steps + 27,488,895
```

At production (81 frames, 480x832, 50 steps, CFG, 30 layers): 209k fewer
host instructions per layer call x 3,000, 254k per forward x 100, about 653M
per video, the constant tax from 6.67 G to 6.02 G (-9.8%). The part that
matters is not the host: the K/V memo removes 2,940 of 3,000 cross-attention
projections, 14.2 TFLOP per video, for 189 MB of bf16 residency. A
per-block constant that no state explained, attributed partly to an sgemm
kernel, was the tell.

---

