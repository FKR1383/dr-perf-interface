# nl-042: pool reallocation with intervening allocation and copy

Use the empty region marker in `include/rapidjson/allocators.h`. Explain its cost with entry-state expressions, using small workloads. Preserve all behavior assertions.

Run `python3 tests/run_case.py --source-root .` from the export. The driver compiles the exact pinned headers with the marked source overlaid, then checks output semantics and target entry at five sizes. Requires Python 3 and a C++11 compiler.
