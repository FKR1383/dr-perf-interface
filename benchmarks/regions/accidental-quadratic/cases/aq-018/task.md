# MIME parameter parsing

Instrument the body of `get_parameter` in `Lib/email/_header_value_parser.py` as region `aq-018`. Keep the source behavior unchanged.

Bounded trigger: Parse a long MIME parameter value.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
