# Declaring and checking waits with drperf

**drperf is a checker. The human or agent declares the semantic dependency;
drperf checks that declaration against observed execution.** It does not discover
the application's intended dependency graph, implement synchronization, or make
an incorrect program wait correctly.

A declaration says: **region A has waited for a particular result published by
region C**. The graph displays `A → C`, from consumer to publisher. The lock,
future, socket, or synchronization helper used to implement that wait need not
be a region.

## Place the checkpoints at the semantic level

Use the same `(event_id, generation)` at both ends:

- `perfmark.event_publish(event_id, generation)`: in C, immediately **before the
  real release** that makes the result available to the consumer.
- `perfmark.event_waited(event_id, generation)`: in A, **after the real wait or
  successful readiness check** has completed.

For example, A calls helper B to wait for C:

```python
import threading
import perfmark

ready = threading.Event()
event_id, generation = 1, 1

# Establish capture before either thread can publish, including with late attach.
with perfmark.region("capture", n=1):
    pass


def C():
    with perfmark.region("C"):
        # Prepare the result here.
        perfmark.event_publish(event_id, generation)
        ready.set()  # The application's real release.


def B():
    ready.wait()  # Ordinary synchronization; no region annotation is required.


producer = threading.Thread(target=C)
producer.start()
with perfmark.region("A"):
    B()
    perfmark.event_waited(event_id, generation)
producer.join()
```

The declaration is **A waits for C**, not B waits for C. If B is marked for
separate instruction accounting, keep `event_waited` outside B, after its region
has ended. It still belongs to A. Different callers can use the same helper for
different dependencies and declare their own events at their call sites.

Similarly, put publication in the region that semantically produces the result;
you do not need to create an artificial region just for the marker. Do not leave
a region open across an `await` that can interleave unrelated coroutines: region
nesting follows execution threads, not asynchronous task identities.

## Event identities, branches, and timeouts

The two numbers are annotation identities, not synchronization objects. Use a
consistent event ID for the logical channel and a fresh generation for each
publication. Both sides must agree on the pair. Within a captured process, each
pair must have exactly one publication; several consumers may wait for it.
Different processes' identical numbers are not matched by the current checker.

There is no condition argument. Original control flow determines whether a
checkpoint executes:

```python
with perfmark.region("A", need=int(need_result)):
    if need_result:
        if ready.wait(timeout=1):
            perfmark.event_waited(event_id, generation)
        else:
            handle_timeout()  # Do not claim successful completion.
```

Already-ready results can also execute `event_waited`: it declares completed
readiness, not that the thread slept. A skipped wait, timeout, cancellation, or
exception must not accidentally execute a successful-wait checkpoint. Declare
PCVs on A if you want drperf to fit how often its wait checkpoints occur.

## Capture and check

From the drperf repository, after building drperf and its Python extension:

```bash
DRPERF_WAITS=1 DRPERF_REPORT=baseline.drperf.json \
  bin/drperf python3 app.py

bin/drperf-check-events baseline.drperf.json --plan
```

The `.drperf.json` is the viewer report: formulas, breakdowns, region traces,
checked dependency results, and graph endpoints. Full synchronization histories
are stored beside it in a checksummed `*.waits.<hash>.jsonl.gz` evidence file;
they are not embedded in the viewer report. VS Code needs only the JSON.
The checking commands load and verify the adjacent evidence automatically.
Keep both files when moving a profile that you want to recheck. Missing or corrupt
evidence prevents rechecking; it never silently becomes an empty wait history.

Wait capture is opt-in. Without `DRPERF_WAITS=1`, an instruction-count report is
not a wait check. Capture must include both publishers and consumers. Late
attachment can miss earlier publications. The Python checkpoint functions
require the built `_perfmark` extension; rebuild with `./build.sh` if needed.

The C equivalents in `perfmark.h` are:

```c
perfmark_event_publish(event_id, generation);
perfmark_event_waited(event_id, generation);
```

The marker calls and their instrumented bodies are excluded from instruction
counting. The application's actual wait and surrounding work retain their normal
accounting.

## Check again while delaying publication

A baseline can look ordered simply because the producer happened to finish
first. `--plan` suggests a publication delay from observed checkpoint distances,
with a bounded maximum. It prints rerun settings; it does not launch the rerun.
For the example above:

```bash
DRPERF_WAITS=1 DRPERF_REPORT=probe.drperf.json \
DRPERF_WAIT_DELAY_KIND=event DRPERF_WAIT_DELAY_REGION=C \
DRPERF_WAIT_DELAY_MS=500 \
  bin/drperf python3 app.py

bin/drperf-check-events probe.drperf.json
```

Drperf delays the publication marker before the following real release. The
consumer's existing synchronization should therefore keep it from reaching
`event_waited` too early. If B does not actually wait, a delayed run can expose
A reaching its checkpoint before C publishes. The markers themselves never
block the consumer on the declared event.

Keep the perturbed run separate from baseline cost measurements. A requested
probe that never reaches its target is reported as unverified, not counted as an
executed check. Delays may also exercise real timeout or cancellation paths.

## What the result establishes

- **Ordered:** each checked consumer checkpoint followed its unique matching
  publication in the observed execution.
- **Violation:** for example, the consumer passed its checkpoint before
  publication completed, or a generation was published more than once.
- **Unverified:** evidence is missing or ambiguous, capture is incomplete, or a
  requested delay was not executed.

The command exits with 0 for ordered declarations, 1 for violations, and 2 for
unverified checks or missing annotations. Passing a delayed run is additional
execution evidence; it is not a proof for every possible schedule or input, nor
proof that the declared producer is necessary for the consumer.

Native synchronization observations are separate evidence. They can flag a
place that needs a declaration even when the primitive's publisher cannot be
resolved. Conversely, an unresolved primitive inside B does not invalidate an
ordered A → C declaration. An ordered declaration does not, by itself, explain
every native synchronization call in A. Missing-declaration coverage and
publication-order checking must be reported separately.
The exported edge's `nativeContext` lists preceding synchronization calls in
that declaring invocation, including descendants such as B. It does not assign
their native objects to C or silently remove them from the unresolved list.
Already-resolved native operations are counted separately as `nativeResolved`.

For GPU work, a CPU-side kernel or copy submission is **not completion**. Do not
label a submission checkpoint as GPU completion. These passive markers check
CPU checkpoint order; stronger device-completion claims need corresponding
captured device evidence.

The runnable [Python example](../examples/waits/events.py) includes a deliberate
`missing-wait` mode. See [wait_task.md](../wait_task.md) for capture details and
[the LMCache study](LMCache_WAITS.md) for application evidence.

Semantic ownership remains an annotation choice. The current checker does not
reject a declaration solely because it belongs to a shared helper, relocate
checkpoints to callers, or prove that a caller's declaration accounts for every
native synchronization inside that helper. Those require additional rules beyond
the publication-order checks described here.
