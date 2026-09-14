# aq-008 rejected candidate

This candidate adapts the parser change from upstream CPython commit
[`476fb09cdb0d73e645849d98c610e7e5697ce7c9`](https://github.com/python/cpython/commit/476fb09cdb0d73e645849d98c610e7e5697ce7c9).
It reduced target instructions by 65.4% on the expanded benchmark matrix, but
it is not accepted as a semantics-preserving optimization. Differential checks
found changed delimiter inference on 37 of 600 valid CSV-writer samples,
including quoted fields containing spaces. The instruction measurements are
retained as rejected-candidate evidence only.
