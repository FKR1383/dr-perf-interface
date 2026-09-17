# Collection provenance

Source: [WanPipeline._get_t5_prompt_embeds](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/pipelines/wan/pipeline_wan.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('prompt_clean_r', tag=922, batch=len(prompt), chars=sum((len(u) for u in prompt)))`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_embeds', tag=921, batch=1 if isinstance(prompt, str) else len(prompt), maxlen=max_sequence_length)`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_forward', tag=923, batch=batch_size, maxlen=max_sequence_length)`
- `videogen/wan-more/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_repad', tag=924, batch=batch_size, maxlen=max_sequence_length, dim=prompt_embeds.shape[2])`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('prompt_clean_r', tag=922, batch=_b, chars=sum((len(u) for u in prompt)))`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_embeds', tag=921, ptok=_b * max_sequence_length, sq=_b * max_sequence_length * max_sequence_length // 64, lsq=max_sequence_length * max_sequence_length // 64)`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_enc', tag=926, ptok=_b * max_sequence_length, sq=_b * max_sequence_length * max_sequence_length // 64, lsq=max_sequence_length * max_sequence_length // 64)`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_forward', tag=923, ptok=_b * max_sequence_length, sq=_b * max_sequence_length * max_sequence_length // 64, lsq=max_sequence_length * max_sequence_length // 64)`
- `videogen/wan-t5/diffusers/pipelines/wan/pipeline_wan.py`: `perfmark.region('t5_repad', tag=924, ptok=_b * max_sequence_length, sq=_b * max_sequence_length * max_sequence_length // 64, lsq=max_sequence_length * max_sequence_length // 64)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
