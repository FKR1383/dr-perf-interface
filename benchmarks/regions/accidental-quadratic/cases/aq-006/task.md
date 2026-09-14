# Variable reference expansion

Instrument the body of `expandvars` in `Lib/posixpath.py` as region `aq-006`. Keep the source behavior unchanged.

Bounded trigger: Expand a long path-like value containing many adjacent variable references.
