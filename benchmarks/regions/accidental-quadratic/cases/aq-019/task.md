# MIME parameter discovery

Instrument the body of `_find_mime_parameters` in `Lib/email/_header_value_parser.py` as region `aq-019`. Keep the source behavior unchanged.

Bounded trigger: Scan a long token sequence for MIME parameters.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
