# Collection provenance

Source: [OfflineInferenceMixin._run_engine](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/entrypoints/offline_utils.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-batch/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-kv/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-out/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-req/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-samp/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-sched/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-spec/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`
- `vllm-cpu-src/vllm/entrypoints/offline_utils.py`: `perfmark.region('generate_loop', unfinished=self.llm_engine.get_num_unfinished_requests())`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
