# Collection provenance

Source: [AutoencoderKLWan._decode](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/models/autoencoders/autoencoder_kl_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_decode_frames', batch=z.shape[0], frames=z.shape[2], height=z.shape[3])`
- `videogen/wan-more/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_frame_loop', frames=num_frame, height=height, width=width, zdim=x.shape[1])`
- `videogen/wan-src/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_decode_frames', batch=z.shape[0], frames=z.shape[2], height=z.shape[3])`
- `videogen/wan-src/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_frame_loop', frames=num_frame, height=height, width=width, zdim=x.shape[1])`
- `videogen/wan-t5/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_decode_frames', batch=z.shape[0], frames=z.shape[2], height=z.shape[3])`
- `videogen/wan-t5/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_frame_loop', frames=num_frame, height=height, width=width, zdim=x.shape[1])`
- `videogen/wan-tax/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_decode_frames', batch=z.shape[0], frames=z.shape[2], height=z.shape[3])`
- `videogen/wan-tax/diffusers/models/autoencoders/autoencoder_kl_wan.py`: `perfmark.region('vae_frame_loop', frames=num_frame, height=height, width=width, zdim=x.shape[1])`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
