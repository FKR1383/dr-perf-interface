# Version field parsing

Instrument the body of `parse_mime_version` in `Lib/email/_header_value_parser.py` as region `aq-015`. Keep the source behavior unchanged.

Bounded trigger: Parse a long malformed version field with repeated separators.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
