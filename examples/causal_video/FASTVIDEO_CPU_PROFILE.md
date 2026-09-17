# FastVideo GX-host CPU IPC profiles

The **current** calibration is the interop=1 managed [CPU-profile run](/home/ubuntu/GX/NEX/build/experiments/fastvideo-cpu81-interop1-1789611176931009711/result.json), with a 9-library loaded cuDNN hash set and `torch_interop_threads=1` recorded by its worker. `gxvm collect` produced `out/causal-video/fastvideo-cpu81-interop1/merged.db` from one shard with no dropped samples. The earlier run below remains a diagnostic of the prior interop=64 setting; do not use its database for the new partial replay.

| Current interop=1 sample | Resolved | Unresolved | Unresolved share of all |
| --- | ---: | ---: | ---: |
| Instructions | 3,328 | 69 | 2.03% |
| Tasks | 1,017 | 5 | 0.49% |

The current merged DB has 17 modules and 546 sampled pages. Applying the replay client's actual gates (at least four instruction and task samples on a page, or at least 32 each on its module) covers **3,154/3,328 resolved instruction samples (94.77%)**, or 92.85% of all instruction samples. Another 174 resolved samples lack page/module coverage. At scale 1.0, the global fallback is `(1017 + 5) / (3328 + 69) = 0.300854 ns/instruction`, since the instruction and task periods are both 5 million in their respective units. A replay startup log must confirm its loaded profile, coverage and scale. The [current evidence manifest](evidence/fastvideo-cpu81-interop1.json) records the raw data and hashes.

Both CPU profiles were collected on the GX host's EPYC 7702P, while native GPU execution uses EPYC 9554. Their path/page hashes do not verify binary identity or ISA dispatch, and sample coverage is not native-host timing accuracy. The worker-only partial timeline omits parent frame-grid CPU work. The current interop=1 native GPU profile must be compared with a complete measured GX partial trace before launch acceptance.

The current CPU run's nine loaded cuDNN DSO basename→SHA-256 entries exactly match both interop=1 native offload and resident timing reports; both native workers also record `torch_interop_threads=1`. This establishes loaded cuDNN library identity for those runs, but it does not establish launch-inventory equality or native CPU calibration. The GX-only `/opt/gx/nccl-payload/lib` search-path prefix remains recorded explicitly.

The current CPU-profile worker interval again contains 106,333 GX prediction events (97,423 regular kernels and 8,910 cuBLAS surrogates), this time across 398 projected signatures. All prediction statuses are `disabled`, as required for this collection role. The distinct-signature count shifted from 396 in the prior CPU run; no launch match is inferred until the new native GPU profile and measured partial trace are available.

## Prior interop=64 diagnostic

The 81-frame FastVideo CPU-profile managed run [passed](/home/ubuntu/GX/NEX/build/experiments/fastvideo-cpu81-ipc-1789610640997916465/result.json) with `metadata_mode=true`, `worker_cpu_output=true`, DiT layerwise offload enabled, and effective FlashAttention for self/cross attention. The measured output shape was `[1, 3, 81, 480, 832]`. `gxvm collect` merged the one worker shard into `out/causal-video/fastvideo-cpu81-ipc/merged.db` with no dropped samples. The [evidence manifest](evidence/fastvideo-cpu81-ipc.json) records the source report, raw/merged DB, trace, logs, and their hashes.

| IPC calibration sample | Resolved | Unresolved | Unresolved share of all |
| --- | ---: | ---: | ---: |
| Instructions | 3,330 | 64 | 1.89% |
| Tasks | 1,025 | 6 | 0.58% |

The profiler sampled 176 threads at 5-million-instruction and 5-ms task periods. Parsing the merged DB with the replay client's exact page/module gates (at least four instruction and task samples on a page, or at least 32 each on its module) gives 3,250 covered resolved instruction samples. That is **97.60% of resolved instruction samples** and 95.76% of all instruction samples; 80 resolved instruction samples lack page/module coverage. The unscaled global fallback is `(1025 + 6) / (3330 + 64) = 0.303771 ns/instruction` because the task and instruction sampling periods are both 5 million in their respective units. A later `partial_sync` replay may apply a cost scale, and its startup log must confirm the actual coverage and scale.

The CPU-profile worker interval's GX trace contains 106,333 prediction-bearing launches: 97,423 regular kernel events and 8,910 cuBLAS surrogate events across 396 projected signatures. All carry `prediction_status=disabled`, as expected for this CPU collection role; they are neither 106,333 hits nor misses. These counts are diagnostic until compared with a fresh native GPU-profile inventory under the same source and output-transfer setting.

The final native GPU-profile DB has the same **106,333 total launches** and 396 projected signatures. The [diagnostic comparison](/home/ubuntu/drperf/out/causal-video/fastvideo-cpu81-ipc/inventory-diagnostic.json) identifies 21 cuDNN `tensorTransformGeneric` launches whose GX grid/block signature differs from native: native `(216,1,1)/(1024,1,1)`, GX `(2045507584,1,1)/(448,1,1)`. No matched-signature metadata mismatch, ambiguous signature, skipped native launch, or missing native sample was found. Strict report identity also differs on Torch interop threads (native 128, GX 64) and `LD_LIBRARY_PATH` (GX prepends `/opt/gx/nccl-payload/lib` to the same cuDNN library path). These differences must be evaluated against the actual partial trace; the CPU-profile trace is not an acceptance pass.

This profile is from the GX host's AMD EPYC 7702P. The real A100 host uses EPYC 9554, and the replay database's absolute-path/page hashes do not prove identical binaries, CPU instructions, or ISA dispatch. Sample coverage therefore measures mapping within this shard, not native-host calibration accuracy. The CPU-profile pass also runs GX emulator code and has a distinct role from the accepted partial timeline; its kernel trace can diagnose launch differences but cannot establish a matched replay or a virtual duration. The final audit must compare the fresh native GPU-profile DB and report with the measured `partial_sync` worker interval.
