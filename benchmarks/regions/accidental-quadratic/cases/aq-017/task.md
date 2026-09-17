# Section token parsing

Instrument the body of `get_section` in `Lib/email/_header_value_parser.py` as region `aq-017`. Keep the source behavior unchanged.

Bounded trigger: Parse a long section token with repeated characters.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
