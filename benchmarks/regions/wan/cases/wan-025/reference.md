# Collection provenance

Source: [WanPipeline.__call__](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/pipelines/wan/pipeline_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('callback_step', tag=907, ninputs=len(callback_on_step_end_tensor_inputs), frames=latents.shape[2], numel=latents.numel())`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('cfg', frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel())`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('cfg_combine', tag=906, frames=latents.shape[2], height=latents.shape[3], numel=latents.numel())`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('denoise_step', batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('step_prep', tag=905, frames=latents.shape[2], numel=latents.numel(), batch=latents.shape[0])`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('vae_stage', zdim=latents.shape[1], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('wan_call', num_frames=num_frames, height=height, width=width, steps=num_inference_steps)`
- `videogen/wan-src/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('cfg', frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel())`
- `videogen/wan-src/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('denoise_step', batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-src/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('vae_stage', zdim=latents.shape[1], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-src/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('wan_call', num_frames=num_frames, height=height, width=width, steps=num_inference_steps)`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('callback_step', tag=907, ninputs=len(callback_on_step_end_tensor_inputs), frames=latents.shape[2], numel=latents.numel())`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('cfg', frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel())`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('cfg_combine', tag=906, frames=latents.shape[2], height=latents.shape[3], numel=latents.numel())`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('denoise_step', batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('step_prep', tag=905, frames=latents.shape[2], numel=latents.numel(), batch=latents.shape[0])`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('vae_stage', zdim=latents.shape[1], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('wan_call', num_frames=num_frames, height=height, width=width, steps=num_inference_steps)`
- `videogen/wan-tax/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('cfg', frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel())`
- `videogen/wan-tax/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('denoise_step', batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-tax/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('vae_stage', zdim=latents.shape[1], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4])`
- `videogen/wan-tax/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('wan_call', num_frames=num_frames, height=height, width=width, steps=num_inference_steps)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
