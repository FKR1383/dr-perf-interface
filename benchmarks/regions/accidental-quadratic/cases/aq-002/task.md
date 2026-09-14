# Type hierarchy ordering

Instrument the body of `ModuleNode.sort_types_by_inheritance` in `Cython/Compiler/ModuleNode.py` as region `aq-002`. Keep the source behavior unchanged.

Bounded trigger: Order a long collection of extension types whose inheritance relationships require repositioning.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
