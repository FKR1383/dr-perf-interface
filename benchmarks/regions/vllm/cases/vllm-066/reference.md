# Collection provenance

Source: [GPUModelRunner._update_states](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/worker/gpu_model_runner.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-batch/vllm/v1/worker/gpu_model_runner.py`: `perfmark.region('update_states', num_reqs=len(scheduler_output.num_scheduled_tokens), num_new=len(scheduler_output.scheduled_new_reqs), num_finished=len(scheduler_output.finished_req_ids))`
- `vllm-cpu-spec/vllm/v1/worker/gpu_model_runner.py`: `perfmark.region('update_states', num_reqs=len(scheduler_output.num_scheduled_tokens), num_new=len(scheduler_output.scheduled_new_reqs), num_draft=sum(map(len, scheduler_output.scheduled_spec_decode_tokens.values())), tag=9006)`
- `vllm-cpu-src/vllm/v1/worker/gpu_model_runner.py`: `perfmark.region('update_states', num_reqs=len(scheduler_output.num_scheduled_tokens), num_new=len(scheduler_output.scheduled_new_reqs), num_finished=len(scheduler_output.finished_req_ids))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
