# Collection provenance

Source: [Scheduler.update_from_output](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/sched/scheduler.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-batch/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_tokens=scheduler_output.total_num_scheduled_tokens)`
- `vllm-cpu-kv/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_tokens=scheduler_output.total_num_scheduled_tokens)`
- `vllm-cpu-out/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_tokens=scheduler_output.total_num_scheduled_tokens)`
- `vllm-cpu-req/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_tokens=scheduler_output.total_num_scheduled_tokens)`
- `vllm-cpu-samp/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_tokens=scheduler_output.total_num_scheduled_tokens)`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_tokens=scheduler_output.total_num_scheduled_tokens)`
- `vllm-cpu-spec/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_draft=sum(map(len, scheduler_output.scheduled_spec_decode_tokens.values())), num_accepted=sum(map(len, model_runner_output.sampled_token_ids)) - sum((1 for _t in model_runner_output.sampled_token_ids if _t)), tag=9008)`
- `vllm-cpu-src/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_from_output', running=len(self.running), num_reqs=len(scheduler_output.num_scheduled_tokens))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
