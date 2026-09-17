# Collection provenance

Source: [InputBatch.refresh_metadata](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/worker/gpu_input_batch.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-batch/vllm/v1/worker/gpu_input_batch.py`: `perfmark.region('refresh_metadata', num_reqs=self.num_reqs, num_added=len(self.batch_update_builder.added), num_moved=len(self.batch_update_builder.moved))`
- `vllm-cpu-samp/vllm/v1/worker/gpu_input_batch.py`: `perfmark.region('refresh_metadata', num_reqs=self.num_reqs, num_new=len(self.batch_update_builder.added), num_removed=len(self.batch_update_builder._removed), num_moved=len(self.batch_update_builder.moved))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
