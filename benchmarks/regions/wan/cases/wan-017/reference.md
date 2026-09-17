# Collection provenance

Source: [WanAttnProcessor.__call__](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/models/transformers/transformer_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn', batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads, kv_len=hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])`
- `videogen/wan-more/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_out', tag=904, seq_len=hidden_states.shape[1], heads=attn.heads, batch=hidden_states.shape[0])`
- `videogen/wan-more/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_qkv', tag=901, seq_len=hidden_states.shape[1], kv_len=hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1], heads=attn.heads)`
- `videogen/wan-more/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_rope', tag=902, seq_len=hidden_states.shape[1], heads=attn.heads, batch=hidden_states.shape[0])`
- `videogen/wan-more/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_sdpa', tag=903, seq_len=hidden_states.shape[1], kv_len=key.shape[1], heads=attn.heads)`
- `videogen/wan-src/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn', batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads, kv_len=hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])`
- `videogen/wan-t5/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn', batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads, kv_len=hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])`
- `videogen/wan-t5/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_out', tag=904, seq_len=hidden_states.shape[1], heads=attn.heads, batch=hidden_states.shape[0])`
- `videogen/wan-t5/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_qkv', tag=901, seq_len=hidden_states.shape[1], kv_len=hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1], heads=attn.heads)`
- `videogen/wan-t5/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_rope', tag=902, seq_len=hidden_states.shape[1], heads=attn.heads, batch=hidden_states.shape[0])`
- `videogen/wan-t5/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn_sdpa', tag=903, seq_len=hidden_states.shape[1], kv_len=key.shape[1], heads=attn.heads)`
- `videogen/wan-tax/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('attn', batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads, kv_len=hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
