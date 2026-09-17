# Collection provenance

Source: [AutoencoderKLWan.encode](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/models/autoencoders/autoencoder_kl_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_encode', tag=913, batch=x.shape[0], frames=x.shape[2], height=x.shape[3])`
- `videogen/wan-t5/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_encode', tag=913, batch=x.shape[0], frames=x.shape[2], height=x.shape[3])`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
