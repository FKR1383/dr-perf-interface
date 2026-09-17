# Parenthesis normalization

Instrument the body of `normalize_invisible_parens` in `src/black/linegen.py` as region `aq-009`. Keep the source behavior unchanged.

Bounded trigger: Normalize a syntax node with many children that require invisible-parenthesis checks.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
