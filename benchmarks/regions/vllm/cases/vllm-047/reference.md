# Collection provenance

Source: [OutputProcessor.process_outputs](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/engine/output_processor.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-out/vllm/v1/engine/output_processor.py`: `perfmark.region('process_outputs', num_outputs=len(engine_core_outputs), num_active=len(self.request_states))`
- `vllm-cpu-src/vllm/v1/engine/output_processor.py`: `perfmark.region('process_outputs', num_outputs=len(engine_core_outputs))`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
