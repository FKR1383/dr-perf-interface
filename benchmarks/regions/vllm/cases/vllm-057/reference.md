# Collection provenance

Source: [NgramProposer.propose](https://github.com/vllm-project/vllm/blob/2cf0a6915ce544dc493a0990f2ea38d81601128a/vllm/v1/spec_decode/ngram_proposer.py).

This location was selected from earlier annotations in the local experiment
archive. The following expressions are historical hypotheses, not a reviewed
answer key or a complexity guarantee:

- `vllm-cpu-spec/vllm/v1/spec_decode/ngram_proposer.py`: `perfmark.region('ngram_propose', num_reqs=len(sampled_token_ids), k=num_speculative_tokens, ctx=int(num_tokens_no_spec[:len(sampled_token_ids)].sum()), tag=9002)`

The source snapshot is exported from pristine Git, and this case patch starts
with zero PCVs. Whole-function cases and child-block cases share a source family
and must remain together when splitting or aggregating a future evaluation.
