# Performance-critical-variable case collection

The current deliverable is a collection of real code regions with **empty
markers**, ready for an agent or human to investigate. It is not a run of a
full agent evaluation pipeline. It contains 1,000 source regions.

The original **207 cases are preserved**, with **793 additions** from compiler
frontends, language tools, and general and native libraries. Each addition has
pinned source, an empty marker, and a test run verified to enter that marker.
See the [growth record](growth/README.md) for execution evidence and independent
checks. The starting groups are:

| Group | Regions | Coverage |
| --- | ---: | --- |
| [vLLM](regions/vllm/) | 67 | Scheduling, requests, sampling, cache management, and output processing |
| [Wan / diffusers](regions/wan/) | 41 | Video pipeline, prompt encoding, attention, VAE, and host orchestration |
| [V8 RegExp](regions/v8-regexp/README.md) | 28 | Matching interpreter, parser, compiler, and experimental engine |
| [V8 JavaScript runtime / bytecode generator](regions/v8-interpreter/README.md) | 50 | Runtime array, string, property and scope paths; bytecode generation |
| [Accidental-quadratic cases](regions/accidental-quadratic/) | 21 | CPython, Cython, Black, and Socket CLI regions linked to upstream performance issues |

These are distinct source targets, not independent bugs. Some whole-function
and child-block targets share a source family, and several parser targets share
one upstream issue. V8 compilation-time regions are labeled separately from
execution-time regions. A runtime fallback marker does not imply that every
JavaScript execution reaches it.


The new slices are [compiler frontends](regions/compiler-frontends/) (250),
[language tools](regions/language-tools/) (250), [general libraries](regions/general-libraries/)
(250), and [native libraries](regions/native-libraries/README.md) (43). All 793
new cases have successful correctness and marker-entry evidence. The compiler
cases use a pinned instrumented LLVM/Clang build; native-library cases compile
pinned RapidJSON headers. This establishes bounded target execution, not full
path coverage or an optimization opportunity in every case.

## Inspect or export a case

```sh
python3 benchmarks/regions/collect.py list
python3 benchmarks/regions/collect.py check
python3 benchmarks/regions/collect.py check --require-tests
python3 benchmarks/regions/collect.py export v8-regexp-001 /tmp/regexp-case
python3 benchmarks/regions/collect.py export aq-001 /tmp/python-case
python3 benchmarks/regions/collect.py test aq-001
python3 benchmarks/regions/collect.py test v8-regexp-001 --d8 /path/to/patched/d8
```

The export contains the source file with its empty marker, the neutral task,
test files and fixtures, public metadata, and applicable licenses. Reference notes and solved historical
annotations stay out of the export. A source file is context for an upstream
checkout; most cases need that project's dependencies before they can run.

The checks validate hashes, revision pins, source locations, independent patch
application, unique targets, and empty markers. For Python, removing the added
marker restores the original AST. For C++, the patch only adds the helper
include and one scope marker. These checks do not establish reachability,
successful upstream compilation, a cost formula, or a performance improvement.
`tests.validation` distinguishes tests that have not run, behavior checks on a
host runtime, and runs verified to enter the marked source region. Passing a
Node test does not prove entry into an internal V8 function. Python tests use
a marker observer to require target entry; when run under drperf, that observer
forwards to the real markers. `build_status: not-built` refers to full upstream
builds, separately from these native Python checks.

See [the collection format and marking instructions](regions/README.md) and
[the machine-readable index](regions/catalog.json).

## Existing records and future evaluation

The [29 historical case families](cases/) retain original evidence, annotation
scripts, patches, and provisional answer keys. The slide deck and full narrative
are under [evaluator/evidence/](evaluator/evidence/). The older
[201-region inventory](evaluator/region-candidates.json) is an expansion queue;
it overlaps both the historical families and the collected targets and must
not be added to the collected-region count.

The earlier [agent-pipeline design](PIPELINE_DESIGN.md), pilot runner and scorer
remain available as deferred evaluation work. The [small-to-large design](SMALL_TO_LARGE.md)
records the hypothesis that symbolic insights from small executions can reduce
the need for expensive large-case runs. The current collection supplies code
targets for testing those ideas later; no agent accuracy or execution savings
are claimed.

Separate [annotation and optimization experiments](growth/README.md) retain
failed rounds, correctness checks, and real drperf measurements. Two measured
workloads show 10.69x and 5.34x target-instruction reductions. These case results
do not establish agent accuracy or complete the with/without-drperf comparison.
