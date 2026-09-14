# FTL lookup call sites

Discover the performance-critical variables (PCVs) of this workload. Locate the
regions whose cost they explain and express the PCVs as computations on state
available at region entry. The cost interface is affine in those expressions;
you do not need to supply its coefficients.

Use code inspection and the measurements allowed by your assigned condition.
Choose experiments that distinguish competing explanations, including changes
to independent inputs. Record your current hypotheses before each measurement,
and submit your revised findings after it. Explain remaining uncertainty.

The task is discovery. Preserve program behavior. Changes for observation and
annotations are allowed; performance fixes are outside this task. Do not replace
a PCV with a computation that re-executes the region or measures its cost.
