# Collection provenance

Source: [VideoProcessor.postprocess_video](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/video_processor.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/video_processor.py`: `perfmark.region('postprocess_video', batch=video.shape[0], frames=video.shape[2], height=video.shape[3], width=video.shape[4])`
- `videogen/wan-more/diffusers/video_processor.py`: `perfmark.region('pp_stack', tag=912, batch=batch_size, frames=video.shape[2], height=video.shape[3])`
- `videogen/wan-src/diffusers/video_processor.py`: `perfmark.region('postprocess_video', batch=video.shape[0], frames=video.shape[2], height=video.shape[3], width=video.shape[4])`
- `videogen/wan-t5/diffusers/video_processor.py`: `perfmark.region('postprocess_video', batch=video.shape[0], frames=video.shape[2], height=video.shape[3], width=video.shape[4])`
- `videogen/wan-t5/diffusers/video_processor.py`: `perfmark.region('pp_stack', tag=912, batch=batch_size, frames=video.shape[2], height=video.shape[3])`
- `videogen/wan-tax/diffusers/video_processor.py`: `perfmark.region('postprocess_video', batch=video.shape[0], frames=video.shape[2], height=video.shape[3], width=video.shape[4])`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
