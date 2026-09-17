# Invalid mailbox recovery

Instrument the body of `get_invalid_mailbox` in `Lib/email/_header_value_parser.py` as region `aq-014`. Keep the source behavior unchanged.

Bounded trigger: Recover from a long malformed mailbox value.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
