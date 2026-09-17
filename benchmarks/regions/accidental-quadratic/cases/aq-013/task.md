# Legacy route parsing

Instrument the body of `get_obs_route` in `Lib/email/_header_value_parser.py` as region `aq-013`. Keep the source behavior unchanged.

Bounded trigger: Parse a long legacy route with repeated separators.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
