# Legacy local-part parsing

Instrument the body of `get_obs_local_part` in `Lib/email/_header_value_parser.py` as region `aq-012`. Keep the source behavior unchanged.

Bounded trigger: Parse a long legacy local-part containing repeated lexical units.
