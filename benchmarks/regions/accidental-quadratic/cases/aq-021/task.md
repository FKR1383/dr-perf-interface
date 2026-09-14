# Encoded-word folding

Instrument the body of `_fold_as_ew` in `Lib/email/_header_value_parser.py` as region `aq-021`. Keep the source behavior unchanged.

Bounded trigger: Fold a long text token into encoded-word output.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
