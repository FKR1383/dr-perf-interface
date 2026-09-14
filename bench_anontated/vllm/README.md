# vLLM annotation results

All 67 exported vLLM regions received at least one instrumented DRPerf attempt.
The final annotation outcomes are:

- 16 `qualified` under the strict affine gate.
- 12 `model-rejected` after reaching the marker but failing state-count or
  unexplained-instruction requirements.
- 36 `annotation-not-qualified` in the delegated 60-second screening cohort.
- 3 `measurement-failed` because the run timed out or produced incomplete raw
  feedback.

Each case keeps its annotated full target source, test fixtures, annotation
patch, raw feedback, metrics, and `result.json`. A result's `final_measurement`
points to metrics matching its final annotated source and fixture state.

The accepted optimization is `vllm-050`: for an unindexed CPU destination,
`_convert_to_tensors` returns the tensor already created on CPU and retains the
original `.to(device)` path for indexed CPU and non-CPU destinations. With the
original region boundary preserved and exact tensor shape/value assertions,
weighted instructions fell from 616,760 to 587,249 (4.78%). Both baseline and
optimized measurements passed the strict gate. Native timing is omitted because
concurrent workloads made wall-clock comparison unreliable.

The `vllm-024` bulk-heapify candidate was rejected. It increased weighted
instructions by 3.34% on the original workload; a larger input grid also exposed
nonlinear behavior and failed the affine gate. Its result records the incomplete
tie-order, self-alias, and empty-input semantic review.
