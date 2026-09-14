# Parameter list parsing

Instrument the body of `_parseparam` in `Lib/email/message.py` as region `aq-007`. Keep the source behavior unchanged.

Bounded trigger: Parse a long semicolon-separated parameter string, including a quoted malformed variant.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
