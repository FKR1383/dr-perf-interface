# Incremental markup parsing

Instrument the body of `HTMLParser.goahead` in `Lib/html/parser.py` as region `aq-004`. Keep the source behavior unchanged.

Bounded trigger: Feed a parser a long incomplete markup sequence and then signal end of input.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
