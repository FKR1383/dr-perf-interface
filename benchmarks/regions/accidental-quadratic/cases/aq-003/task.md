# Quoted value decoding

Instrument the body of `_unquote` in `Lib/http/cookies.py` as region `aq-003`. Keep the source behavior unchanged.

Bounded trigger: Decode one quoted cookie value containing many escaped characters.
