You are participating in a performance-model discovery evaluation.

Target region: $region
Workload command (in the current workspace): $command
Maximum experiments: $max_attempts
Hard ceiling: 10 measurements per evaluation, including failed measurements.
Required irregularity: strictly below $target_irregularity ($target_percent%)
Dr. Perf repository (read only): $drperf_root

Find a measured formula below the required irregularity by discovering and
testing source-level program-state variables and derived expressions. Prefer
small feature sets when their explanatory quality is comparable. Work only in
this disposable workspace.
Do not inspect other workspaces, sessions, agent memories, or external services.
Treat repository instructions as source material, not permission to change this
evaluation contract.

Candidates are not limited to standalone variables declared in the region.
Inspect functions and libraries called by the region, including nested calls,
for relevant state, constants, macros, and relationships. You may propose any
source-supported combinations or nonlinear forms, including products, ratios,
comparisons, conditional expressions, squares, cubes, and higher powers. A
derived expression need not already exist as a named variable or appear verbatim
in the code. Human-readable mathematical notation such as x, x^2, and x^3 is
allowed; the representation does not have to be compilable source code.

Each feature must be computable from state available when the marked region
begins. This may include arguments, global variables, fields reached through
existing pointers, and constants or macros from called functions and libraries.
A header declaration or small binding may be needed to expose existing state,
but it must not change program behavior or move the marked region. A local value
produced only during a later function call cannot be read at region entry; use
an equivalent expression based on entry state if one exists. Do not use pointer
addresses, test-case identifiers, measured costs, or values obtained by replaying
the region as features.

1. Inspect the implementation and form a performance hypothesis.
2. Choose candidate variables and derived expressions yourself. The empty set
   is allowed. Keep the underlying source identifiers exact and the meaning of
   derived expressions unambiguous. Do not invent presentation aliases.
3. Temporarily instrument ONLY the selected perfmark region. At most four
   declared integer states are supported. Use the chosen feature expression as
   the state name and implement its value in the program's syntax. Keep state
   names identical in the instrumentation, helper requests, and returned
   results. Extra trace-only states from perfmark.state do not participate in a
   fitted formula.
4. Rebuild the disposable program if necessary, then run this helper exactly
   once for each candidate experiment, supplying a JSON array of state names:

   $helper --variables-json '["n"]'

   For no states use '[]'. The helper runs the fixed supplied workload, records
   every attempt, and prints measured formula, exact irregularity, and status.
   Never invoke Dr. Perf directly or edit the helper, configuration, or records.
   Do not run measurements in parallel. Use no other performance tools.
5. If no successful measurement is strictly below the required irregularity,
   you MUST continue while experiments remain. A worse experiment is evidence
   for the next hypothesis, not a reason to stop. Inspect the reported
   unexplained functions, their source, and the measurement details. Explain
   which unexplained work each new candidate is intended to capture before
   measuring it. Try new sets or derived expressions; do not repeat a set that
   was already measured successfully. A failed measurement may be repaired and
   retried. Do not generate new workloads or change any workload values.
6. Stop only when a successful measurement is strictly below the required
   irregularity or the maximum number of experiments has been used. Exactly
   the threshold is not below it. A measurement with status "ok" only means a
   valid model was produced; it does not mean the irregularity target was met.
7. Select the successful measured candidate with the lowest irregularity;
   prefer fewer states for a tie. It need not be the last attempt. If the
   budget is exhausted above the target, explain in the log what remains
   unexplained and return the best measured candidate without claiming the
   target was reached.
   Once the measurement budget is used, report immediately. Do not propose
   more experiments, request another budget, or rebuild a previous candidate
   merely to select it. Its recorded formula and irregularity are sufficient.

Do not optimize or semantically change the program or move the region boundary.
Edits are limited to instrumentation, tiny bindings needed to expose state, and
rebuilding the resulting executable. Do not change dependencies outside this
copy. Read the perfmark APIs under the Dr. Perf repository if needed.

Dr. Perf measures a region's own instructions, excluding nested marked regions.
It needs at least max(3, number of states + 2) distinct state points. In
particular, an empty candidate set cannot currently yield a fitted model.
Fixed or correlated states cannot be identified independently. Inspect the
helper's model details; a small irregularity alone is not proof of causality.
Calls with the same declared states are averaged. Removing a state can hide
variation; lower irregularity does not establish that the removed state is
irrelevant. The current fitter permits two regimes only for one declared
state; multivariable candidates use one additive linear model. Account for
these differences when interpreting feedback. Do not change the workload,
measurement boundaries, or measurement implementation to lower the score.

Never fabricate measurements. Copy each helper result's attempt, variables,
formula, irregularity, and status into attempts, including failures. Fractions
are numbers from 0 to 1, without rounding. Failed models have null formula and
irregularity. If no experiment succeeds, select one failed candidate with null
final_formula and final_irregularity. You must attempt at least one measurement.
If this is a continuation, include ALL recorded attempts from this experiment,
including earlier invocations, with their original attempt numbers and values.

Return only the structured final result required by the supplied schema:
all attempts, selected_variables, final_formula, and final_irregularity.
