# Native library regions

43 hand-selected RapidJSON function regions at commit `24b5e7a8b27f42fa16b96fc70aade9106cf7102f`: DOM copies, lookup, allocation, ordered erasure, serialization, pointer traversal and token copying. Each independent patch adds exactly one empty RAII marker and a helper include.

Each case has a C++ workload with concrete semantic assertions at sizes 1, 2, 7, 16 and 65. The shared driver extracts the pinned header archive, overlays the exported marked source, compiles with C++11 and runs it. A native observer requires balanced target entry at every size. All 43 passed; see `validation.json`. These checks establish region execution, not drperf counts or performance-interface fits.

```
python3 benchmarks/regions/collect.py test nl-001
```

No external checkout is needed for tests. Python 3.12 and `c++` were used for validation. `CXX` selects another compiler. `generate_cases.py PINNED_CHECKOUT` regenerates collection assets; regeneration resets validation labels to not-run. The shared archive contains pristine headers and the project license is retained in `upstream/rapidjson/LICENSE`.

Different cases may target functions in one call chain. Split evaluations by project or call family to prevent closely related code from leaking across training and test sets. The collection makes no claim that all these functions admit a large optimization.

The test observer forwards to the real PerfMark library when `PERFMARK_LIB` is set. Under `DRPERF` that library is required; the observer cannot silently substitute native-only checks. `drperf-smoke/` records a successful real instrumented `nl-001` run. Its empty annotation produces one aggregate state and correctly fails the model gate for insufficient states. This smoke check establishes that future annotations can use the same workload driver for drperf feedback. It does not claim the cost has been explained.
