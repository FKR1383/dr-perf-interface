## A pure-CPU system: the Kimi Code CLI's cold start, halved

The GPU sections above end on a gate: a host-side fix pays only where the
accelerator waits for the host. A CLI startup has no accelerator, so every
instruction drperf attributes is on the wall clock, and the loop closes
without a caveat. The target is `kimi-cli` 1.50.0 from PyPI, the Kimi Code
CLI, a Python coding agent. Nothing here touches a network: the run ends
at "LLM not set", so the whole measurement is local startup work.

```
python3 -m venv kimi-venv && ./kimi-venv/bin/pip install kimi-cli   # 1.50.0
export PYTHONPATH=/home/ubuntu/drperf-cases/kimi-mark:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
/home/ubuntu/drperf/bin/drperf-dev run --blocks -q --threads 1 --repeat 2 \
    --max-slots 4194304 --state n_tools=1,2,3,4,5,7,8,9,11,13,14,15,16,17 \
    -o out/kimi_fit2 -- ./kimi-venv/bin/python startup/run_kimi.py
```

`startup/run_kimi.py` generates an agent spec holding the first `n_tools`
of the seventeen default tools and runs `kimi --quiet -p hi` in-process
against a fresh `KIMI_HOME`. The package is copied to `kimi-mark/` and put
first on `PYTHONPATH`; `startup/mark.py` inserts the regions, so the marked
tree is reproducible from the pristine one.

**Beat one, the fit.** The obvious state for tool loading is how many tools
there are. drperf refuses it. `derive out/kimi_fit --region load_tools`
splits the range in two and the upper half does not fit:

```
cost(n_tools) = 40,976,735.8*n_tools + 67,426,198.8   [n_tools <= 7]    8.8% irregular
cost(n_tools) =  7,127,579.0*n_tools + 161,553,133.7  [n_tools >= 9]   89.6% irregular
```

89.6% irregular is the tool saying the cost is not a function of the count.
Adding the import-closure size as a second state made it worse (99.9%),
and the raw per-point sums say why: from one tool to seven the region grows
87.1M to 382.9M while `sys.modules` grows by five entries, then the eighth
tool alone adds 1,103M and the fourteenth adds 1,942M. The cost is not
affine in anything, because it is a step function of *which* tools are in
the list. The per-call region says it exactly (`out/kimi_probe`, 17 tools):

| tool | modules it adds | instructions |
|---|---|---|
| `tools.file:ReadFile` (idx 7) | 511 | 1,100,526,152 |
| `tools.web:SearchWeb` (idx 13) | 163 | 1,936,996,159 |
| the other fifteen | 0 to 5 each | 34.5M to 87.1M each |

**Beat two, the surprise.** Two of seventeen tools are 80% of tool loading,
and the reason is a module import each of them triggers.

- `kimi_cli/tools/file/read_media.py:7` reads
  `from kosong.chat_provider.kimi import Kimi`, used once, at line 121, for
  an `isinstance` test. That import is the **OpenAI SDK, 495 modules**. It
  is on the startup path because `tools/file/__init__.py` imports every
  sibling, so asking for `ReadFile` pays for it.
- `kimi_cli/tools/web/fetch.py:5` reads `import trafilatura`, called once,
  at line 102, inside the tool body. That import is an **HTML extraction
  stack: `trafilatura`, `lxml`, `dateparser`, `courlan`, `justext`,
  `htmldate`, `tld`, `pytz`, 166 modules**.
- With those gone, `deferred_import` became the largest region at 3.84G of
  5.68G, and inside it `kimi_cli/soul/toolset.py:30` reads
  `from kosong.tooling.mcp import convert_mcp_content`, called once, at line
  1065, when an MCP tool returns content. That import is the **whole Model
  Context Protocol package, about 300 modules of pydantic models**, loaded
  whether or not any MCP server is configured.
- What was left was not an import. `kosong/tooling/__init__.py:30` validates
  every tool's parameter schema at construction with
  `jsonschema.validate(self.parameters, Draft202012Validator.META_SCHEMA)`.
  The convenience call re-checks the meta-schema against its own meta-schema
  on each of the sixteen calls; building the validator once takes the same
  sixteen validations from 88ms to 9ms.

Each of the four is one line moved or reused. None changes what the program
computes: the imports happen on first use, the validator is the same
validator.

**Beat three, the fix, measured both ways.** Instructions from drperf with
identical markers on both trees (`out/kimi_before2`, `out/kimi_after3`);
wall clock from nine fresh processes per tree (`startup/bench.py`).

| region | before | after | change |
|---|---|---|---|
| process total | 8,655,375,049 | 4,064,157,769 | -53.0% |
| `cli_run` | 7,981,039,387 | 3,541,961,150 | -55.6% |
| `deferred_import` | 3,840,262,560 | 2,758,304,318 | -28.2% |
| `app_create` | 3,963,574,710 | 604,566,911 | -84.7% |
| `load_tools` | 3,773,522,741 | 415,268,876 | -89.0% |
| `boot_import` | 69,988,404 | 69,975,975 | 0.0% |

| cold start, 9 processes | best | median |
|---|---|---|
| stock 1.50.0 | 2.055 s | 2.083 s |
| four fixes | 0.916 s | 0.923 s |

**-53.0% instructions, -55.7% wall clock.** The two agree to 2.7 points,
which is the whole point of a pure-CPU target: here drperf's instruction
count *is* the time, with no gate in between. Startup goes from 2.08s to
0.92s, a 2.3x speedup, from four one-line edits that a profiler would have
shown as "import machinery" and drperf attributed to the four call sites
that cause it.

**Equivalence.** `startup/equiv.py` builds every tool from the default
agent spec on both trees and digests the names and JSON parameter schemas:
`55c7f09cb96db3f8` on both. `startup/functest.py` then exercises the four
changed call sites: `trafilatura.extract` on a fixture returns the same
markdown, `convert_mcp_content` on a text block returns the same part, the
`Kimi` provider class still resolves, and a malformed parameter schema is
still rejected by the now-cached validator. Both trees print the same
record. The four edits are collected in `kimi_fixes.patch`.

**Why this case exists.** The three GPU sections above measure real work
removed that the wall clock did not show, because an A100 was waiting on
something else. This one measures the same kind of work removed on a
machine where nothing else is waiting, and the wall clock moves by exactly
the amount the instruction count predicted. Both halves are needed: the
formula tells you what the work is and where it comes from, and the gate
tells you whether removing it will be visible.

