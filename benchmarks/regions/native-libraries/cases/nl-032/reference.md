# Evaluator reference: nl-032

Pinned source: https://github.com/Tencent/rapidjson/blob/24b5e7a8b27f42fa16b96fc70aade9106cf7102f/include/rapidjson/pointer.h#L390

Target: `bool operator<(const GenericPointer& rhs)` (occurrence 1). Workload: lexicographic pointer ordering. Sizes 1, 2, 7, 16, 65; each must enter the marker and satisfy exact semantic assertions. These are separate function regions, some in the same call chain; split by upstream project/call family to avoid evaluation leakage.

This is a collection lead, not a demonstrated optimization. Native observer assertions establish execution, not drperf instruction counts or a fitted interface.
