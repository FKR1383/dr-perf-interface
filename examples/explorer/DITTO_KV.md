# Ditto-KV: capture a fresh profile and inspect it in VS Code

The input to the extension is a measured `.drperf.json` file. The exporter
reads raw counters and traces; it does not read `# drperf` comments or parse
`report_costs.txt`. Keep the executable `@marked(...)` and `with region(...)`
annotations. Saved formula comments can be removed.

Open `/home/ubuntu/compression/ditto_kv` as the VS Code workspace. Its directory
name contains an underscore, not a hyphen. Run the shell commands below on the
workstation containing that checkout and `/home/ubuntu/drperf`.

## What needs rerunning?

- Changed only the viewer: reinstall the VSIX; keep the JSON.
- Changed only fitting, composition, or marker-accounting analysis: re-export
  the existing raw measurements with the current exporter.
- Changed the profiler/client, program, PCVs, workload, or GX boundary behavior:
  capture again, then export that new run. Re-exporting old counters is not a
  new measurement.

Export after removing comments if you want the source links to use the new line
numbers. Source hashes describe the files at export time; they do not prove
that edited program logic matches an older capture.

## Fresh capture on the existing GX experiment host

These commands use the already provisioned `ubuntu@icdslab2.epfl.ch` setup:
`~/ditto_kv_gx`, image `gx-kimi-k3:latest`, its cached model metadata/native
extensions, and `gxvm_runtime/gx_cuda_mixedfake.so`. They are not instructions
for provisioning a new machine. The workloads use dummy weights and plain GX
functional emulation. Do not launch GXVM or a timing simulation for these CPU
instruction measurements.

### 1. Build and stage the current profiler and application

Do this when no other drperf capture is using the shared staged tree.

```bash
export DITTO_PROFILE_HOST=ubuntu@icdslab2.epfl.ch
export DITTO_PROFILE_REMOTE=/home/ubuntu/ditto_kv_gx

cd /home/ubuntu/drperf
./build.sh
DRPERF_RUNTIME_DIR=$(readlink third_party/dynamorio)
rsync -aR bin/ lib/ perfmark/ build/*.so \
  third_party/dynamorio "third_party/$DRPERF_RUNTIME_DIR/" \
  "$DITTO_PROFILE_HOST:$DITTO_PROFILE_REMOTE/drperf/"

cd /home/ubuntu/compression/ditto_kv
rsync -a --exclude __pycache__ --exclude native/build src/ \
  "$DITTO_PROFILE_HOST:$DITTO_PROFILE_REMOTE/src/"
rsync -a --exclude __pycache__ --exclude runs exp/gx_kimi/ \
  "$DITTO_PROFILE_HOST:$DITTO_PROFILE_REMOTE/exp/gx_kimi/"
```

This stages the runtime and client as one bundle. The existing Ditto launcher
otherwise prefers `gxvm_runtime/libdrperf_gxdr.so` and its matching attach
library, which can be older. The explicit paths in the next command override
that preference. The Python marker extension must match the experiment's
Python 3.12; the current workstation build and staged image use that version.

### 2. Launch one preset

Choose `qwen` first. Repeat this section with `kimi` after fetching Qwen. Each
capture gets a new directory and container; old profiles are not overwritten.

```bash
export DITTO_PROFILE_PRESET=qwen    # use kimi for the second capture
export DITTO_PROFILE_RUN="drperf-offline-${DITTO_PROFILE_PRESET}-current-$(date +%Y%m%d-%H%M%S)"

ssh "$DITTO_PROFILE_HOST" bash -s -- "$DITTO_PROFILE_PRESET" "$DITTO_PROFILE_RUN" <<'REMOTE'
set -eu
preset=$1
run=$2
root=/home/ubuntu/ditto_kv_gx
cpus=16
memory=40g
if [ "$preset" = kimi ]; then cpus=48; memory=44g; fi
mkdir -p "$root/runs/$run"
docker run -d --name "$run" --cpus "$cpus" \
  --memory "$memory" --memory-swap "$memory" --ipc host \
  --security-opt seccomp=unconfined --cap-add=SYS_PTRACE --cap-add=SYS_ADMIN \
  -v "$root:/w" -v "$root/drperf:/home/ubuntu/drperf:ro" \
  -v "$root/gxvm_runtime/gx_cuda_mixedfake.so:/home/jma/GX/src/sims/gpu/gx_cuda.so:ro" \
  -e PRESET="$preset" -e RUN="/w/runs/$run" \
  -e DRPERF_ROOT=/home/ubuntu/drperf -e DRPERF_MODE=late \
  -e DRPERF_DRRUN=/home/ubuntu/drperf/third_party/dynamorio/bin64/drrun \
  -e DRPERF_CLIENT=/home/ubuntu/drperf/build/libdrperf.so \
  -e DRPERF_ATTACH=/home/ubuntu/drperf/build/libdrperf_attach.so \
  -e DRPERF_ATTACH_UNMASK_SIGNAL=1 -e DRPERF_NATIVE_GX=1 \
  -e DRPERF_EXCLUDE_CUDA_MODULE=gx_cuda.so \
  -e DRPERF_MAX_STATES_PER_REGION=4096 -e DRPERF_TIMEOUT=14400 \
  --entrypoint /bin/bash gx-kimi-k3:latest -lc \
  'bash /w/exp/gx_kimi/drperf_offline.sh > "$RUN/driver.log" 2>&1'
REMOTE
printf 'Capture: %s\n' "$DITTO_PROFILE_RUN"
```

The script keeps its native warm-up and late attachment. Qwen uses one emulated
GPU, 24 sessions and six turns by default. Kimi uses eight emulated H200s,
three sessions and two turns. Kimi's engine and eight workers should produce
nine raw run files. This is a CPU-cost experiment, not a latency comparison.

### 3. Wait, check completion, and fetch

```bash
ssh "$DITTO_PROFILE_HOST" docker wait "$DITTO_PROFILE_RUN"
ssh "$DITTO_PROFILE_HOST" \
  "tail -20 '$DITTO_PROFILE_REMOTE/runs/$DITTO_PROFILE_RUN/driver.log'"

# The capture writes as root. Make its files readable before fetching them.
ssh "$DITTO_PROFILE_HOST" docker run --rm \
  -v "$DITTO_PROFILE_REMOTE/runs/$DITTO_PROFILE_RUN:/r" \
  --entrypoint /bin/chmod gx-kimi-k3:latest -R a+rX /r

cd /home/ubuntu/compression/ditto_kv
mkdir -p "exp/gx_kimi/runs/$DITTO_PROFILE_RUN"
rsync -a "$DITTO_PROFILE_HOST:$DITTO_PROFILE_REMOTE/runs/$DITTO_PROFILE_RUN/" \
  "exp/gx_kimi/runs/$DITTO_PROFILE_RUN/"
```

`docker wait` should print `0`; the driver should report successful completion.
If it times out, inspect `driver.log`, `serve.log`, and `server.log` before
exporting. A killed process may never flush its counters. Check that Kimi has
all nine process reports. Do not silently omit a failed worker.

### 4. Export the fresh capture

```bash
cd /home/ubuntu/compression/ditto_kv
/home/ubuntu/drperf/bin/drperf-export \
  "exp/gx_kimi/runs/$DITTO_PROFILE_RUN/raw" \
  --source-root "$PWD" --max-trace 100000 \
  -o "exp/gx_kimi/runs/$DITTO_PROFILE_RUN/$DITTO_PROFILE_PRESET.drperf.json"
```

All raw process reports in that directory are pooled automatically, with their
trace histories kept separate. Do not point this command at a directory mixing
old and new captures. Preserve the `.json.blocks`, `.json.slots`, and
`.json.trace` sidecars alongside each raw `run.*.json`.

Check the exported result:

```bash
python3 - "exp/gx_kimi/runs/$DITTO_PROFILE_RUN/$DITTO_PROFILE_PRESET.drperf.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
print('Processes:', len(m['provenance']['runs']))
print('Regions:', len(m['regions']))
print('Mapped to source:', sum(bool(r['sources']) for r in m['regions']))
print('Trace:', m['trace']['recordCount'], 'complete:', m['trace']['complete'])
print('Composition:', m['composition']['status'])
print('Relationship discovery:', m['discovery'])
for run in m['provenance']['runs']:
    d = run['measurement']
    print(run['file'], 'GX native hooks:', d.get('native_gx_hooks'),
          'GX native calls:', d.get('native_gx_calls'))
errors = m['validity']['errors'] + m['validity']['traceErrors']
assert not errors, errors
assert m['trace']['complete'], 'Incomplete trace: no complete child-call composition'
assert m['composition']['status'] == 'observed', m['composition']['errors']
PY
```

Missing GX native hooks, counter/state overflow, or dropped trace events need
attention before treating the results as complete. The viewer supports up to
100,000 trace events and a 50 MiB JSON file. A larger capture should be split
into smaller workloads; lowering the trace limit keeps own-region fits but
disables complete child composition. Relationship discovery has a separate
search/feature-table budget and may be skipped even with a complete trace.

After fetching and verifying a run, remove only its stopped container with
`ssh "$DITTO_PROFILE_HOST" docker rm "$DITTO_PROFILE_RUN"`. Keep its raw data
if you expect to change the analysis again. Repeat sections 2–4 with `kimi`.

## Re-export an existing capture without running the model

For the two original captures, these commands update analysis only. The current
fitter accepts any nonempty set of observed states, including a constant fit at
one state, and fits child-call multipliers without a minimum-state cutoff.
Re-export to replace old “more varied states needed” results; no new capture or
VS Code extension change is required. Fits still describe only observed states.

```bash
cd /home/ubuntu/compression/ditto_kv
qwen_run=exp/gx_kimi/runs/drperf-offline-qwen-late16-evictable-20260923-042415
kimi_run=exp/gx_kimi/runs/drperf-offline-kimi-late3-final-20260923-040329
/home/ubuntu/drperf/bin/drperf-export "$qwen_run/raw" \
  --source-root "$PWD" --max-trace 100000 -o "$qwen_run/qwen.drperf.json"
/home/ubuntu/drperf/bin/drperf-export "$kimi_run/raw" \
  --source-root "$PWD" --max-trace 100000 -o "$kimi_run/kimi.drperf.json"
```

## Open the profile and follow nested calls

1. Install `/home/ubuntu/drperf/out/drperf-explorer-0.1.4.vsix` using
   **Extensions: Install from VSIX**, then **Developer: Reload Window**.
2. Open `/home/ubuntu/compression/ditto_kv`, run **drperf: Open Performance
   Report**, and select the new Qwen or Kimi `.drperf.json`.
3. Click a region. Its source opens beside the formula, observed-state table,
   and unexplained-function breakdown. If using another workspace root, set
   `drperf.sourceRoot` to `/home/ubuntu/compression/ditto_kv`.
4. A parent keeps direct children symbolic, for example
   `34*n + 33 + (2*n + 1)*F[child]`. Click `F[child]` to navigate to the
   child's interface and source. The child retains its own unexplained work
   and descendants; it is not replaced by a global average. Unknown call multipliers remain
   unexplained; argument mappings are kept separately. Recursion is not expanded.

Displayed costs and percentages are rounded to whole numbers. The JSON and
calculations retain their original precision; a displayed zero coefficient
can therefore be a small nonzero fitted value. Call-count and argument
relations keep exact fractions such as `n/2`. Charts and function attribution
remain **own-region** measurements; symbolic composition is not a prediction
of elapsed time or parallel execution.

## Marker accounting after the calibration removal

Current exports exclude marker-library and native binding blocks by identity;
they do not subtract calibrated Python wrapper estimates. Ditto-KV's existing
`pcv(...)` helper brackets its computation in `perf.pcv`, which remains excluded
from application interfaces and nested composition. Remaining Python wrapper and
marker-boundary work stays measured. Ordinary PCV expressions outside that helper
are not automatically excluded.

Use the re-export commands above on existing raw captures to apply this change.
A fresh capture is unnecessary for this accounting change. Previously exported
JSON retains its old formulas and calibration warnings until replaced by a new
export. New drperf launches no longer request automatic wrapper calibration;
calibration samples present in older captures are ignored for subtraction.
