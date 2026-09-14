# Conditional Statement Generation

Instrument `v8::internal::interpreter::BytecodeGenerator::VisitIfStatement` with the `v8-interpreter-019` RAII region marker. The selected phase is Ignition bytecode generation during JavaScript compilation. Use the bounded workload described in `case.json`; its test command and validation status are recorded there.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
