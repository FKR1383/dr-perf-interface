# Environment token expansion

Instrument the body of `expandvars` in `Lib/ntpath.py` as region `aq-005`. Keep the source behavior unchanged.

Bounded trigger: Expand a long path-like value containing many adjacent environment-variable references.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
