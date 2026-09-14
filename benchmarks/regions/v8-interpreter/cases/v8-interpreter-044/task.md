# Object Entry Enumeration Slow Path

Instrument `v8::internal::Runtime_ObjectEntriesSkipFastPath` with the `v8-interpreter-044` RAII region marker. The selected phase is JavaScript execution. Use the bounded workload described in `case.json`; its command remains unverified.
