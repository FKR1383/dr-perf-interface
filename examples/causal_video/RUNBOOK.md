# Repeating the measurements

These commands assume the study's existing A100 and GX workspaces, pinned
model assets, compatibility dependencies, drperf bundle, and isolated GX
runtime are already staged. They are not a fresh-machine installer. The
source revisions are in `pins.json`; source preparers reject unexpected
inputs. Large weights, native output tensors, and traces remain outside Git.
The two baseline [GPU databases](evidence/kernel-databases/README.md) and their
native reports are included as compressed artifacts. Evidence manifests
identify the remaining recorded artifacts.

Run one GX job at a time. The managed launcher checks memory, stages its
runtime, collects artifacts, and stops its containers. Wait for a successful
`result.json` with empty `cleanup_errors` before starting the next job.

## Native reference and GPU database

For Inferix, from this repository:

```bash
python3 examples/causal_video/native_run.py --name inferix-reference-new \
  --repetitions 3 --save-output
python3 examples/causal_video/native_run.py --name inferix-profile-new \
  --role gpu-profile
```

Keep the source tree, KV residency, shapes, and metadata mode identical in
native profiling and GX. The optimized Inferix tree additionally removes the
discarded decode; `--rope-cache --kv-residency gpu` selects the separate CPU
candidate. Compare native outputs before interpreting latency differences.

For the matched FastVideo transport adapter, run the staged profile script
inside the existing native container through the managed helper:

```bash
python3 examples/wan_gx/native_container.py command \
  'bash /workspace/causal/code/fastvideo_gpu_profile.sh fastvideo-profile-new metadata FastVideo-metadata off on'
```

The last two arguments select resident DiT weights and worker CPU output,
respectively. Use the worker database, which contains the generation kernels;
do not accidentally select the parent process database. Check all signatures
have usable samples. The script fixes library paths, attention backend, and
thread settings; preserve those settings in native timing and GX.

## GX CPU profile, drperf, and partial timing

From this repository, generate each configuration separately. Here `GPU_DB`
is the absolute path to that matched native worker database, and `CPU_DB` is
the subsequently collected CPU database. These shell variables must be set
to the actual artifact paths.

```bash
python3 examples/causal_video/config.py fastvideo cpu-profile \
  --name fastvideo-cpu-new --gpu-db "$GPU_DB" --worker-cpu-output \
  --output out/causal-video/fastvideo-cpu-new.json

python3 examples/causal_video/config.py fastvideo drperf \
  --name fastvideo-drperf-new --gpu-db "$GPU_DB" --worker-cpu-output \
  --drperf-bundle out/causal-video/drperf-bundle \
  --output out/causal-video/fastvideo-drperf-new.json

python3 examples/causal_video/config.py fastvideo partial_sync \
  --name fastvideo-partial-new --gpu-db "$GPU_DB" --cpu-db "$CPU_DB" \
  --worker-cpu-output \
  --timeline-client out/causal-video/gxvm-timeline-exclude/build/libgxvm_timeline_client.so \
  --output out/causal-video/fastvideo-partial-new.json
```

Launch each selected configuration from `/home/ubuntu/GX/NEX`:

```bash
SSH_BASE_PORT=24420 python3 container_cmds/run.py /absolute/path/to/config.json
```

After CPU profiling, copy the worker's `host-0/d0/profile-*.db` files into a
new collection directory and run `tools/gxvm/gxvm collect DIRECTORY` from
GX/NEX. Its `merged.db` becomes `CPU_DB`. Retain unresolved-sample counts;
page-match coverage alone overstates the calibration coverage.

For Inferix, substitute `inferix` and omit `--worker-cpu-output`. Its default
request is 21 latent frames; FastVideo's is 81 pixel frames. The corrected
timeline client is built using [these instructions](gxvm_timeline_cuda_cpu_exclusion.md).
drperf and GX timing instrumentation run separately.

## Acceptance and interpretation

Generate a full report from a completed partial run with
`tools/gxvm/gxvm report RUN --output NEW_REPORT_DIRECTORY` in GX/NEX. From this
repository, summarize it and compare native and emulated launch inventories:

```bash
python3 examples/causal_video/summarize_partial.py "$REPORT_DIR" \
  --run-dir "$RUN_DIR" --output-prefix out/causal-video/partial-screen
python3 examples/causal_video/audit_kernel_trace.py \
  --native-db "$GPU_DB" --native-report "$NATIVE_REPORT" \
  --gx-report "$GX_REPORT" --trace "$GX_KERNEL_TRACE" \
  --output out/causal-video/kernel-audit.json
python3 examples/causal_video/summarize_drperf.py "$DRPERF_RUN_DIR" \
  --output-prefix out/causal-video/drperf-summary
```

`GX_KERNEL_TRACE` is the worker's raw `kernel_profile_gx/chrome_trace_PID.json`,
not the reconstructed report trace. Use marked virtual iteration durations,
not application clocks, for partial timing. FastVideo's modeled interval is
worker-only; parent frame assembly remains outside its modeled CPU work.
Failed inventory gates, missing prediction service, omitted transfer costs,
and CPU calibration differences must accompany any timing interpretation.
Only warmed, unprofiled native runs establish an end-to-end speedup.
