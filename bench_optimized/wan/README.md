# Wan optimization results

Sixteen gate-qualified Wan cases were reviewed. Fourteen retain their annotated source with `status: no-change` because no local improvement was found that clearly preserves public semantics and region boundaries.

`wan-007` and `wan-008` use a broadcast tensor blend for nonoverlapping extents greater than one, retaining the scalar loop for extent one and overlapping tensors. The same positive-extent workload reduced aggregate counted instructions by 23.07% and 23.54%, respectively. At extent one, the final horizontal-blend run regressed by 0.49% and the vertical-blend run improved by 0.20% (an earlier vertical run regressed slightly), and the optimized affine explanation remains above the 5% unexplained threshold; both limitations are recorded in the case results.

Separate correctness tests compare the optimized output against the original scalar loop for extents -1, 0, 1, 2, and 3, aliasing, and four floating dtypes. They use rtol=atol of 1e-12 for float64, 1e-6 for float32, 1e-3 for float16, and 1e-2 for bfloat16. These are numeric tolerance checks rather than bitwise equivalence claims.
