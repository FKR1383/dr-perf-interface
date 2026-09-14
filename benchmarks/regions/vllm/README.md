# vLLM regions

This collection contains 67 regions from the pinned vLLM source snapshot. Every
case has a bounded Python correctness and marker-reachability test. The exported
test bundle receives two shared resources: `driver.py` supplies the real vLLM
scenarios, and `marker_probe.py` observes the empty `perfmark.region` marker.

Run a case from its directory with the pinned CPU environment:

```text
HF_HOME=/home/ubuntu/drperf/third_party/hf \
/home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python \
tests/test_case.py --source-root /path/to/patched/source
```

The driver enables Hugging Face offline mode, uses the cached
`facebook/opt-125m` model, limits generation to three prompts with one to three
output tokens, and keeps the V1 engine in-process so marker observations remain
visible to the probe. Prefix-cache cases use an explicitly enabled cache and a
shared prefix longer than one cache block. Sampler cases use stochastic top-k and
top-p inputs, while rejection-sampler and n-gram cases enable n-gram speculative
decoding. Queue, request, list-removal, penalty, and CPU top-k/top-p cases use
smaller direct API scenarios instead of loading a model.

Correct output is necessary but does not establish region coverage. Each test
ends with `Probe.finish(case_id)`, which fails unless the exact patched marker was
observed. Scheduler, cache, sampler, and engine fast paths vary with configuration;
their manifests state target-specific verification status. In the pinned source,
`CPUModelRunner` inherits `_prepare_inputs`, `_update_states`, and `execute_model`
from `GPUModelRunner`, so cases 065–067 are valid CPU reachability candidates.

The direct scenarios and specialized speculative, stochastic-sampling, and CPU
model-runner scenarios passed their value assertions in the provided pinned CPU
environment. Cases 014–025, 039, 049–057, and 065–067 were run with their
individual patch applied to a detached-file hardlink clone of the pinned
checkout; their exact markers were observed and are labeled `region-verified`.
The other 42 cases are `not-run` against their individual patches and retain
target-specific unverified status.
