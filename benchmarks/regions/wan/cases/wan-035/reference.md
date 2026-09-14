# Collection provenance

Source: [WanPipeline.encode_prompt](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/pipelines/wan/pipeline_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('encode_prompt', batch=len(prompt) if isinstance(prompt, list) else 1 if prompt is not None else prompt_embeds.shape[0])`
- `videogen/wan-src/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('encode_prompt', batch=len(prompt) if isinstance(prompt, list) else 1 if prompt is not None else prompt_embeds.shape[0])`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('encode_prompt', batch=len(prompt) if isinstance(prompt, list) else 1 if prompt is not None else prompt_embeds.shape[0])`
- `videogen/wan-tax/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('encode_prompt', batch=len(prompt) if isinstance(prompt, list) else 1 if prompt is not None else prompt_embeds.shape[0])`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
