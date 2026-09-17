# Collection provenance

Source: [LLMEngine.add_request](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/engine/llm_engine.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-req/vllm/v1/engine/llm_engine.py`: `perfmark.region('engine_add_request', num_tokens=len(prompt.get('prompt_token_ids') or ()) if isinstance(prompt, dict) else len(prompt) if isinstance(prompt, str) else 0)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
