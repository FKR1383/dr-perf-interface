# Private Brand Installation

Instrument `v8::internal::Runtime_AddPrivateBrand` with the `v8-interpreter-041` RAII region marker. The selected phase is JavaScript execution. Use the bounded workload described in `case.json`; its test command and validation status are recorded there.

The `tests/` bundle supplies small inputs and correctness assertions. Keep these
checks passing while investigating the empty marker.
