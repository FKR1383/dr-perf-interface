# Evaluator reference: nl-041

Pinned source: https://github.com/Tencent/rapidjson/blob/24b5e7a8b27f42fa16b96fc70aade9106cf7102f/include/rapidjson/allocators.h#L321

Target: `void* Malloc(size_t size) {` (occurrence 2). Workload: pool allocation across chunk capacity. Sizes 1, 2, 7, 16, 65; each must enter the marker and satisfy exact semantic assertions. These are separate function regions, some in the same call chain; split by upstream project/call family to avoid evaluation leakage.

This is a collection lead, not a demonstrated optimization. Native observer assertions establish execution, not drperf instruction counts or a fitted interface.
