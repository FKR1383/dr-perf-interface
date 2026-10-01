# Agent 2 — Dr. Perf measurer

Start this as a separate session that can access the Dr. Perf repository, its
built runtime, the controller directory, and the submitted attempt. It must not
edit or suggest PCVs. Its task is to invoke `evaluation/evaluate.py measure` and
report infrastructure problems to the human operator.

The trusted controller, rather than the language model, computes acceptance. It
retains full metrics under the attempt and writes only redacted feedback into
Agent 1's directory.

