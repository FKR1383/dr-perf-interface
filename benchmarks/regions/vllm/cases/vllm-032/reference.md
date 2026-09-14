# Collection provenance

Source: [Scheduler.schedule](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/sched/scheduler.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-batch/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-kv/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-out/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-req/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-samp/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('sched_preempt', running=len(self.running), preempted=len(preempted_reqs), num_new_tokens=num_new_tokens)`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('sched_running_eval', running=len(self.running), num_computed=request.num_computed_tokens, num_tokens=request.num_tokens)`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('sched_waiting_eval', num_tokens=request.num_tokens, num_computed=request.num_computed_tokens, waiting=len(self.waiting))`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('sched_waiting_loop', waiting=len(self.waiting), skipped=len(self.skipped_waiting), running=len(self.running))`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('sched_waiting_result', admitted=len(scheduled_new_reqs) + len(scheduled_resumed_reqs), n_skipped=len(step_skipped_waiting), waiting=len(self.waiting))`
- `vllm-cpu-sched/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-spec/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`
- `vllm-cpu-src/vllm/v1/core/sched/scheduler.py`: `perfmark.region('schedule', running=len(self.running), waiting=len(self.waiting))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
