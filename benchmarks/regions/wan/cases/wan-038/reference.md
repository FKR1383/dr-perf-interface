# Collection provenance

Source: [FlowMatchEulerDiscreteScheduler.set_timesteps](https://github.com/huggingface/diffusers/blob/c5469b7ceb606edd7ba6570dcd17d38590a18db6/src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `videogen/wan-more/diffusers/schedulers/scheduling_flow_match_euler_discrete.py`: `perfmark.region('set_timesteps', steps=num_inference_steps or 0)`
- `videogen/wan-src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py`: `perfmark.region('set_timesteps', steps=num_inference_steps or 0)`
- `videogen/wan-t5/diffusers/schedulers/scheduling_flow_match_euler_discrete.py`: `perfmark.region('set_timesteps', steps=num_inference_steps or 0)`
- `videogen/wan-tax/diffusers/schedulers/scheduling_flow_match_euler_discrete.py`: `perfmark.region('set_timesteps', steps=num_inference_steps or 0)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
