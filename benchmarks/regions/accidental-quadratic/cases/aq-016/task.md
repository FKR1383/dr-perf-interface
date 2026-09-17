# Invalid parameter recovery

Instrument the body of `get_invalid_parameter` in `Lib/email/_header_value_parser.py` as region `aq-016`. Keep the source behavior unchanged.

Bounded trigger: Recover from a long malformed MIME parameter.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
