# Deferred Constant Allocation

Instrument `v8::internal::interpreter::BytecodeGenerator::AllocateDeferredConstants` with the `v8-interpreter-012` RAII region marker. The selected phase is Ignition bytecode generation during JavaScript compilation. Use the bounded workload described in `case.json`; its command remains unverified.
