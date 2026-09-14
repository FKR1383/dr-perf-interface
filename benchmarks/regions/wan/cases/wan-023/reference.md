# Collection provenance

Source: [WanTransformer3DModel.forward](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/models/transformers/transformer_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('transformer_forward', batch=hidden_states.shape[0], frames=hidden_states.shape[2], seq_len=hidden_states.shape[2] // self.config.patch_size[0] * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2]))`
- `videogen/wan-src/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('transformer_forward', batch=hidden_states.shape[0], frames=hidden_states.shape[2], seq_len=hidden_states.shape[2] // self.config.patch_size[0] * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2]))`
- `videogen/wan-t5/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('transformer_forward', batch=hidden_states.shape[0], frames=hidden_states.shape[2], seq_len=hidden_states.shape[2] // self.config.patch_size[0] * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2]))`
- `videogen/wan-tax/diffusers/models/transformers/transformer_wan.py`: `perfmark.region('transformer_forward', batch=hidden_states.shape[0], frames=hidden_states.shape[2], seq_len=hidden_states.shape[2] // self.config.patch_size[0] * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2]))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
