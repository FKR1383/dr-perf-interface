# Member registration

Instrument the body of `_proto_member.__set_name__` in `Lib/enum.py` as region `aq-001`. Keep the source behavior unchanged.

Bounded trigger: Construct an enumeration with many distinct hashable member values.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
