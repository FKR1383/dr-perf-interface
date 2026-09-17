# Collection provenance

Source: [Scheduler._free_request](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/core/sched/scheduler.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-req/vllm/v1/core/sched/scheduler.py`: `perfmark.region('sched_free_request', running=len(self.running), num_blocks=len(self.kv_cache_manager.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())), num_tokens=request.num_tokens)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
