# `partial_sync` CUDA CPU accounting candidate

`partial_sync` uses `tools/gxvm/experimental/timeline/client.c` and loads `libgxvm_timeline_client.so`. The first Inferix report's 45.396 s modeled CPU work is suspect: the corresponding drperf pass excluded 95.084 billion instructions inside CUDA API calls, whereas the timeline client charged their translated `gx_cuda.so` code. Its 51.814 s virtual interval is diagnostic, not a workload timing result.

[`gxvm_timeline_cuda_cpu_exclusion.patch`](gxvm_timeline_cuda_cpu_exclusion.patch) adds one per-thread raw TLS slot for a nested CUDA-export exclusion depth. It enumerates exported CUDA APIs in `gx_cuda.so`, wraps entry and exit, and skips both the modeled-cost debit and CPU sampling while inside a wrapped API. Calls still execute. `gxvm_timeline_cpu_units()` reads the unchanged counter within the boundary, so stamps remain monotonic. Framework instructions outside wrapped calls remain chargeable. It logs export, entered-call and outer-scope counts at exit. The patch is based on the shared GX timeline `client.c` SHA-256 `078f8e93af69518899cf131fa096e1f140cc8a3a0815e8325feb2342cbe60cb0` and `CMakeLists.txt` SHA-256 `5554fbc8a223f4940753e1447e36ea9bee3285c7915c03d7dfda495febb519d3`; the shared GX tree was not edited.

The built isolated client is `/home/ubuntu/drperf/out/causal-video/gxvm-timeline-exclude/build/libgxvm_timeline_client.so`. Set managed experiment JSON `runtime.timeline_client` to this absolute path, along with the selected `runtime.gx_library`. The managed launcher stages `runtime.timeline_client` as `libgxvm_timeline_client.so` for `partial_sync`. `runtime.client` selects the different native epoch scheduler and has no effect here.

Rebuild from the pinned GX source into an empty isolated directory without editing GX:

```bash
python3 examples/causal_video/prepare_gx_timeline.py \
  --gx-root /home/ubuntu/GX/NEX \
  --output /home/ubuntu/drperf/out/causal-video/gxvm-timeline-exclude-rebuild
```

The script checks both patch-base hashes, copies `client.c`, `sampling.c`, `sampling.h`, and `CMakeLists.txt`, links the GX scheduler/extension dependencies read-only, applies the patch, and builds with `-DDynamoRIO_DIR=/home/ubuntu/GX/NEX/build/gxvm-install/stage/dynamorio/cmake` by default. Supply `--dynamorio-dir` if your GX install differs. It writes `build-manifest.json` with patch, dependency, and output-library hashes. Use its printed library path for `runtime.timeline_client`. A clean rebuild completed locally. The CPU-only regression command is:

```bash
python3 examples/causal_video/gxvm_timeline_exclusion_toy/run.py \
  --drrun /home/ubuntu/GX/NEX/build/gxvm-install/stage/dynamorio/bin64/drrun \
  --baseline-client /home/ubuntu/GX/NEX/build/gxvm-timeline/libgxvm_timeline_client.so \
  --patched-client /home/ubuntu/drperf/out/causal-video/gxvm-timeline-exclude-rebuild/build/libgxvm_timeline_client.so
```

The CPU-only [`gxvm_timeline_exclusion_toy/run.py`](gxvm_timeline_exclusion_toy/run.py) compiles a mock `gx_cuda.so` with nested CUDA calls and mock stream/event state changes and stamps. It checks identical output under the baseline and patched clients; monotonic stream/event stamps; a constant CPU stamp during the nested CUDA work; strictly growing stamps across host work; and six outer exclusion scopes for seven wrapped calls. The local run reduced the CUDA-region counter delta from about 6.55 billion to 106,496 fixed-point units, with identical head and tail host-loop deltas. The remaining delta includes host call-site instructions between stamps. This test has no GPU and cannot establish real kernel/stream/event dependency semantics.

The toy source stays under `examples/`; its earlier generated binaries and baseline/patched logs are preserved under ignored `out/causal-video/gxvm-timeline-exclusion-toy/artifacts/`. The current `run.py` builds fresh binaries in a temporary directory.

The full managed Inferix `partial_sync` workload has now completed with this `runtime.timeline_client`; [its result and audit](PARTIAL_RESULTS.md) include nonzero exclusion counts and preserved dependency records. The observable launch inventory still fails on 168 cuDNN plan variants. The timeline model also omits some host/GPU dependencies and models copies with zero GPU service, so the result remains optimistic rather than a guaranteed hardware lower bound.
