# Workspace file discovery

Instrument the body of `Core.find_files` in `socketsecurity/core/__init__.py` as region `aq-010`. Keep the source behavior unchanged.

Bounded trigger: Discover files for a bounded workspace with overlapping filename patterns.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
