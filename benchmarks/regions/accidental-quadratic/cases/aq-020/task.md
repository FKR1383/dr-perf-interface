# Transfer encoding parsing

Instrument the body of `parse_content_transfer_encoding_header` in `Lib/email/_header_value_parser.py` as region `aq-020`. Keep the source behavior unchanged.

Bounded trigger: Parse a long malformed transfer-encoding field.
