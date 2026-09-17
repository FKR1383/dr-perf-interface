# Measured results: full Wan under GX emulation

Official pretrained Wan2.1-T2V-1.3B, 832x480, 81 frames, 50 UniPC steps,
CFG 5, seed 42, no offload, native CUDA convolution backend. Both variants use
the common control-metadata fixes. See [scope and reproduction](README.md).

Recorded marked CPU instructions: **23.632 billion -> 18.945 billion
(19.84% reduction)**. Each region contributes only its own count,
so the total does not double-count nested calls. GX module residue is zero in
both final records; collection validity checks pass. The CPU count includes
annotation overhead and does not include unmarked worker threads or GPU work.

Unmarked GX generation host seconds (three consecutive generations after one
model load per variant):

* Baseline: 10.731, 9.436, 9.460.
* Optimized: 9.271, 7.986, 8.017.
* Median: 9.460 -> 8.017 seconds
  (15.25% lower).

These are emulator host elapsed times, with first-use work included in each
first generation. The experiment is small, sequential, and not a statistical
hardware-performance study. Loading takes about 75 seconds and is excluded
from generation comparisons. No predicted GPU latency or video quality claim
follows from these numbers. Profiled elapsed times in the JSON include DynamoRIO
overhead and are not used to claim speedup.

GX reused an existing 1 GiB shared arena despite the requested 8 GiB policy and
logged soft-real allocations spilling to fake backing. The application completed;
these runs do not use collectives. GX allocation work is excluded from drperf
region counts, but its overhead participates in unmarked host timings. We did
not delete pre-existing shared IPC state. A fresh arena can change these timings.

| Region | Calls baseline / optimized | Baseline M instructions | Optimized M instructions | Reduction |
| --- | ---: | ---: | ---: | ---: |
| wan_flash_attention | 6,000 / 6,000 | 4013.00 | 3727.69 | 7.11% |
| wan_vae_conv | 692 / 692 | 2951.18 | 2951.34 | -0.01% |
| wan_block | 3,000 / 3,000 | 2850.05 | 2845.42 | 0.16% |
| wan_transformer | 100 / 100 | 2439.84 | 2431.27 | 0.35% |
| wan_model_to | 50 / 1 | 2360.84 | 47.39 | 97.99% |
| wan_rope_apply | 6,000 / 6,000 | 2275.86 | 1322.77 | 41.88% |
| wan_self_attention | 3,000 / 3,000 | 2183.09 | 2180.08 | 0.14% |
| wan_cross_attention | 3,000 / 3,000 | 1818.68 | 1124.86 | 38.15% |
| wan_rms_norm | 12,000 / 9,060 | 1686.06 | 1265.11 | 24.97% |
| wan_layer_norm | 9,100 / 9,100 | 457.20 | 456.52 | 0.15% |
| wan_vae_residual | 294 / 294 | 203.02 | 202.09 | 0.46% |
| wan_scheduler | 50 / 50 | 95.19 | 94.82 | 0.38% |
| wan_generate | 1 / 1 | 51.60 | 50.70 | 1.74% |
| wan_t5_encoder | 2 / 2 | 48.24 | 48.38 | -0.29% |
| wan_vae_resample | 63 / 63 | 36.99 | 37.09 | -0.27% |
| wan_vae_decoder | 21 / 21 | 33.35 | 33.24 | 0.32% |
| wan_t5_attention | 48 / 48 | 31.10 | 31.11 | -0.04% |
| wan_head | 100 / 100 | 27.14 | 27.19 | -0.16% |
| wan_t5_ffn | 48 / 48 | 19.06 | 19.20 | -0.71% |
| wan_time_embedding | 100 / 100 | 18.74 | 18.73 | 0.08% |
| wan_vae_attention | 21 / 21 | 13.31 | 13.28 | 0.19% |
| wan_tokenize | 2 / 2 | 10.67 | 10.66 | 0.02% |
| wan_vae_clear_cache | 2 / 2 | 4.18 | 2.23 | 46.67% |
| wan_vae_decode | 1 / 1 | 3.39 | 2.86 | 15.83% |
| wan_encode_text | 2 / 2 | 0.60 | 0.60 | -0.04% |

Most regions have insufficient distinct states for an affine fit at this fixed
workload. Mixed VAE convolutions and scheduler steps still have substantial
unexplained cost. A successful structural run or fewer instructions is not an
accepted performance interface. The JSON retains these failed/absent fits,
reconstruction errors, and all exclusion diagnostics.

Compact evidence: [baseline](evidence/baseline.json),
[optimized](evidence/optimized.json). These include source and client hashes,
raw-artifact hashes, runtime policy and package versions. Raw block/trace files
remain under `out/wan-gx/results/{baseline,optimized}-final-profile/raw/`.
Earlier exploratory measurements with narrower CUDA exclusions are superseded
by this matched comparison.
