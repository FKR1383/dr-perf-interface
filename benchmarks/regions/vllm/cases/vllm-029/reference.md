# Collection provenance

Source: [Scheduler._update_after_schedule](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/sched/scheduler.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_after_schedule', num_reqs=len(scheduler_output.num_scheduled_tokens), num_tokens=scheduler_output.total_num_scheduled_tokens, num_new=len(scheduler_output.scheduled_new_reqs))`
- `vllm-cpu-src/vllm/v1/core/sched/scheduler.py`: `perfmark.region('update_after_schedule', num_reqs=len(scheduler_output.num_scheduled_tokens))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
