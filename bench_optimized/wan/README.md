# Wan optimization results

## Measurement scope

The experiments in this directory run actual patched Diffusers regions on
**small CPU tensors**. They do not run pretrained Wan video generation end to
end on a GPU. The [fixture](wan-007/tests/helper.py) constructs tiny random
models and tensors; drperf counts CPU interpreter, dispatch, and tensor-kernel
instructions. The percentages below are instruction reductions for the tested
regions, not GPU or end-to-end speedups.

## Current blend patches

Sixteen gate-qualified Wan cases were reviewed. Fourteen retain their annotated source with `status: no-change` because no local improvement was found that clearly preserves public semantics and region boundaries.

`wan-007` and `wan-008` use a broadcast tensor blend for nonoverlapping extents greater than one, retaining the scalar loop for extent one and overlapping tensors. The same positive-extent workload reduced aggregate counted instructions by 23.07% and 23.54%, respectively. At extent one, the final horizontal-blend run regressed by 0.49% and the vertical-blend run improved by 0.20% (an earlier vertical run regressed slightly), and the optimized affine explanation remains above the 5% unexplained threshold; both limitations are recorded in the case results.

Separate correctness tests compare the optimized output against the original scalar loop for extents -1, 0, 1, 2, and 3, aliasing, and four floating dtypes. They use rtol=atol of 1e-12 for float64, 1e-6 for float32, 1e-3 for float16, and 1e-2 for bfloat16. These are numeric tolerance checks rather than bitwise equivalence claims.

| Case | Source change | Measurement and limitations |
| --- | --- | --- |
| Horizontal blend | [wan-007 patch](wan-007/optimization.patch) | [wan-007 result](wan-007/result.json): 23.07% fewer aggregate instructions; maximum optimized unexplained share 21.28% |
| Vertical blend | [wan-008 patch](wan-008/optimization.patch) | [wan-008 result](wan-008/result.json): 23.54% fewer aggregate instructions; maximum optimized unexplained share 20.95% |

Both patches replace repeated Python indexing and tensor dispatch with a
broadcast expression over the overlap. They retain the scalar path for extent
one or overlapping storage, and return unchanged output for nonpositive extents.
The result records say `accepted-with-model-limitation`, with `gate_pass: false`:
measured instruction reductions do not imply that the new interface is fully
explained. GPU behavior and performance of these patches remain untested here.

## Earlier discoveries and the GPU follow-up

The historical evidence describes a separate set of experiments:

- [Wan A](../../benchmarks/cases/wan_a/reference/record.md): rotary-table and
  text-projection caching, plus list-then-concatenate VAE output. Read the
  correction to the original VAE cost attribution as well as the findings.
- [Wan B](../../benchmarks/cases/wan_b/reference/record.md): hoisting callback
  `locals()`, lazy posterior statistics, and rotary application. It also reports
  a **slower** vectorized blend at production-shaped CPU inputs (21.9 to
  27.4 ms), showing why the recent tiny blend results must not be generalized.
- [Wan C](../../benchmarks/cases/wan_c/reference/record.md): caching fixed
  cross-attention K/V and removing redundant per-step work.
- [Wan D](../../benchmarks/cases/wan_d/reference/record.md): reducing text-encoder
  padding, while preserving the transformer's output sequence shape. Removing
  downstream padding keys was rejected because it changed model behavior.

The archived [real-GPU follow-up](../../benchmarks/evaluator/evidence/CASES.md#the-wan-fixes-on-a-real-gpu-no-wall-clock-change-and-why-that-is-the-honest-answer)
reports pretrained Wan2.1-T2V-1.3B on an A100-SXM4-80GB in bfloat16. For 81 frames
and 30 steps, baseline / earlier fixes without T5 / all earlier fixes took
98.831 / 98.897 / 98.992 seconds: **no meaningful end-to-end speedup**. The
non-T5 fixes preserved the latent digest; shortening T5 padding changed it.
An altered digest alone does not establish acceptable numerical or perceptual
equivalence. The tiny CPU equivalence checks do not settle that GPU question.

This is a linked historical report, not a fresh GPU validation of the patches
in this directory. Its main lesson is that removing real work need not shorten
the critical path of a GPU-bound video pipeline.
