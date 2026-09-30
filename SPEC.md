# drperf: what it computes

**Measurement.** `perfmark_begin(ρ, x, v)` (`perfmark_begin_v`: all declared
states, with dynamically sized storage) … `perfmark_end(ρ)` around a code region yields a *trigger*
$t$: region $\rho(t)$, declared state vector $v(t) \in \mathbb{Z}^k$, thread
$\tau(t)$, sequence numbers $b(t) < e(t)$ from one atomic counter shared by
all threads. DynamoRIO attributes every executed
user-space instruction to the innermost open trigger of its thread, or the
leader thread's if it has none. $n_\beta(t)$ is the number of instructions of
basic block $\beta$ attributed to $t$ on all threads;
$\mathrm{cost}(t) = \sum_\beta n_\beta(t)$. Counts are exact and, for
deterministic single-threaded programs, reproducible to the instruction. Only
per-point means $c_\beta(v)$ over triggers with $v(t) = v$ are stored, for at
most 4,096 points per region by default (configurable with
`DRPERF_MAX_STATES_PER_REGION` or the client option `-max_states_per_region`)
and within a bounded counter allocation; calls
beyond either are counted and reported, not placed at a point.  Blocks beyond
the counter table are merged into one slot, which is reported and invalidates
the run. Counter arrays share a 96-GiB virtual-address budget. A separate
process-wide bound of 65,536 region keys, including overflow buckets, terminates
measurement with an explicit error if reached. The raw report records these
budgets and the allocated counter bytes.

**Optional measurement scope.** `DRPERF_FOLLOW_THREADS=0` attributes instructions
only while their own thread has an open region; unmarked workers do not inherit
the leader's region. `DRPERF_NATIVE_EXEC_MODULES=basenames` requests native
execution of whole modules (experimental DynamoRIO `-native_exec_list`);
this bypasses instrumentation and is not a validated GX measurement mode
(see README). `DRPERF_EXCLUDE_CUDA_MODULE=basename` suppresses the selected
module's blocks and synchronous callees beneath its exported CUDA driver/runtime
and cuBLAS/cuDNN/cuSOLVER/cuSPARSE/cuFFT/cuRAND/cuTENSOR APIs. Exclusion depth is
thread-local and nested; normal return restores counting. Asynchronous callee
work on another thread is outside this stack scope. Raw output records the
scope, matched exports, call count and excluded instructions. The latter is a
process-wide diagnostic, not a per-region cost. An exclusion matching no exports
invalidates the run. These options change what cost means; compare identical
scopes and check remaining module attribution. Non-GX programs retain the
measurement above. Counting exclusion alone still instruments execution.

Loading `gx_cuda.so` automatically enables its CUDA-module exclusion and
executes its `gxvm_gpu_native_run` entry and its dynamic callees natively, returning
to instrumented host code afterward. This additional device-work boundary can
also be used on emulator worker threads. Native work contributes no instruction
counts, including to the `excluded_instructions` diagnostic. Raw metadata
records installed boundaries and native calls. It is for functional GX, without
GXVM timing. GX loader/dispatch stubs remain instrumented.
`DRPERF_NATIVE_GX=0` (`-no_auto_gx`) disables automatic GX handling. Explicit
`DRPERF_NATIVE_GX=1` with a CUDA-module selection supports renamed emulators.
Do not combine GX work-boundary replacement with whole-module native execution.

**Cost formulae (`derive`).** Over the observed points $V \subset \mathbb{Z}^k$,
$|V| \ge 1$, each block gets a least-squares plane
$a_\beta \cdot v + d_\beta$; tolerance $\theta(y) = \max(64,\ 0.05\,y)$.
$\beta$ is *affine* if $|c_\beta(v) - a_\beta \cdot v - d_\beta| \le \theta(c_\beta(v))$
for all $v \in V$; a negative intercept is allowed because the origin need
not belong to the input domain (e.g. `cost = a*(depth-1)`). It *scales* in
variable $j$ if moreover $|a_{\beta j}|(\max V_j - \min V_j) > \theta(\max_v c_\beta)$
or the points are exactly coplanar with $a_{\beta j} \ne 0$ (other slopes
are folded into the constant); a block scaling in no variable is *constant*;
every other block is *irregular*.

$$\mathrm{cost}(v) \approx A \cdot v + D,\qquad A_j = \sum_{\text{scaling in } j} a_{\beta j},\quad D = \sum_{\text{affine}} d_\beta' + \sum_{\text{constant}} \operatorname{mean}_v c_\beta(v),$$

with $I(v) = \sum_{\text{irregular}} c_\beta(v)$ tabulated at $V$ only.
OpenMP runtime blocks are excluded as waiting. Before fitting, perfmark library
and native Python binding blocks are excluded by identity. No calibrated wrapper
profile is subtracted, including when an older capture contains calibration
samples. Python wrapper execution and caller-side argument preparation remain
measured unless explicitly excluded. PCV computation placed in a `perf.pcv`
region is isolated by exclusive counters and omitted from exported application
interfaces and their composition.
There is no minimum-state or full-rank requirement: one state gives a constant,
and underdetermined fits select independent columns. Variables constant or
collinear over $V$ cannot be separated and are recorded in fit metadata.
For $k = 1$ and an irregular share above 5%, $V$ may be split
once into two regimes of at least 3 points (3 is flagged weak), chosen by
the mean per-point irregular fraction. Guaranteed: exactly affine counts give exact predictions on $V$
(P1; coefficients need not be unique); at
$v \in V$ the error is at most $\sum_{\text{affine}} \theta$ (P2); irregular
cost never enters $A$ or $D$ (P3). Not provided: loop detection or
data flow (the only link to $v$ is co-variation across $V$: an undeclared
variable shows as irregular if independent, hides in $D$ if balanced across
$V$, is charged to $v$ if correlated), non-affine
forms (curves such as $n \log n$ can pass as a plane over a limited range;
the sign of $D$ does not establish curvature), regimes in more than one variable, checked extrapolation beyond
$V$, min–max intervals.

**Relationships (`learn`).** For a trigger $t$ of region $A$ with state $x$,
over every region $R$ and state $u$:
$\mathrm{count}_R(t) = |\{t' : \rho(t') = R,\ b(t') < b(t)\}|$,
$\mathrm{cum}_{R,u}(t) = \sum u(t')$ over that set, $\mathrm{last}_{R,u}(t)$ =
$u$ of its latest member, $\mathrm{cumend}_{R,u}(t) = \sum u(t')$ over
$\{\rho(t') = R,\ e(t') < b(t)\}$. `learn` reports every
$x(t) = \sum_{j \in S} \gamma_j \varphi_j(t) + \delta$ with $|S| \le 3$,
$\gamma_j \in \{\pm 1, \pm 2\}$, holding exactly at every trigger of $A$
(in integer arithmetic, so "exact" means exact);
otherwise a least-squares fit, labelled approximate. Guaranteed: an exact
relation describes the run, not an estimate (R1). Not provided: relations
through undeclared variables, causality, happens-before (the order is the
counter's), protection against coincidence when candidates outnumber
triggers, so a relation counts only if exact in every run.

**Composition.** The basic-block fit remains a region's *own* cost: instructions
counted while it was the innermost open region. A separate symbolic composition
uses direct-child calls in the same thread, process, and run. Function boundaries
do not matter. Child interfaces are frozen; their blocks are never refitted
against parent PCVs. For each parent invocation, the trace supplies the child
call count and child arguments. The checker finds an affine call-count relation
in the parent PCVs, checking every invocation in exact rational arithmetic
(including parents with zero child calls). The parent uses the basis terms
`F_child` and `PCV*F_child`, written compactly as `(a*PCVs + d)*F_child`.
F is an atomic reference to the child's full interface, including its
unexplained component and descendants. It is not expanded into the parent.

Child-argument mappings are optional metadata. The checker tries affine maps
in parent PCVs and, for varying arguments, an invocation index. Neither map is
required to accept an affine multiplier. Actual child-state histograms are
retained in the JSON report. In particular, a single call with unmapped child
PCVs is still `1*F_child`, not a summation. If no affine multiplier explains
call count, the parent retains `unexplained(F_child)` rather than introducing
a summation outside the chosen interface basis. A semantic parent PCV such as
`selected_count` can make that multiplier affine. Recursion stays symbolic.

The final unexplained report retains the same multipliers:
`U_parent = U_own_parent + (a*PCVs + d)*U_child`. An unmodelled multiplier leaves
the full child contribution in `unexplained(F_child)`. An irregular child does
not prevent a compact parent interface. A product `N*F`
denotes N applications of that interface, not N times the child's global
measured mean. The client aggregates block counts by region/state across callers;
it does not record block counts per invocation or per caller. Raw traces do
record thread-local per-invocation self/inclusive totals, whose scope differs
from the runtime-filtered, potentially all-thread block fits. Consequently this
composition does not claim exact inclusive instruction totals for individual
parents. Own-fit tolerance, repeated-state averaging, and unexplained-cost
limitations persist. Numerical inclusive predictions require additional assumptions
or finer block counters. No cross-thread parentage, parallel latency, or unobserved
input guarantee is inferred.

Composition uses the already marker-adjusted own fits, without adding marker
costs back. Raw counts and separately fitted `recordedRegimes` remain available
for audit and the recorded-count view. Marker-module exclusion removes only
instructions actually observed in identifiable marker blocks; no estimated cost
is subtracted or added. Remaining wrapper and marker-boundary overhead can
matter for tiny or frequently entered regions. Arbitrary PCV expressions are
not automatically excluded: explicitly bracket expensive annotation work in a
`perf.pcv` region. Re-exporting an older raw capture applies these rules without
requiring a new execution; previously exported JSON retains its old accounting.
Missing/crossing traces, omitted state buckets, and invalid measurements disable
composition. The exporter also disables it when the trace exceeds its configured
limit. Affine call relations are fitted on any nonempty set of parent/index
points, without requiring more observations than their design-matrix rank;
dependent PCVs are disclosed. Every relation, including a constant at a single
input, describes observations only. Conflicting call counts at the same input
still fail the exact relation check.

`composition.check` checks a frozen composition against a separate execution's
trace and per-state counter coverage. It checks each available multiplicity and
argument relation in exact arithmetic without refitting, preserves unexplained
child multipliers, reports new call-graph edges, distinguishes absent parents from
zero child calls, and rejects incompatible PCV schemas. PCV name order and JSON
object-key order do not change argument meaning. This validates structural
relations at the newly observed calls, not predictions of their instruction
cost or unknown U values. A context-dependent shared child can have an affine
global state mean and yet fail badly as a numerical cost prediction for one
caller; the composition examples include this negative control and its PCV
refinement.
