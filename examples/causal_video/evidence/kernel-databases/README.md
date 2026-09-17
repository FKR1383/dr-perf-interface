# Native A100 kernel databases

These are the actual databases used for the final baseline GX partial runs,
compressed without changing their contents. `manifest.json` records compressed
and uncompressed SHA-256 hashes. Decompress into an ignored output directory
and use the resulting SQLite file as `config.py --gpu-db`:

```bash
mkdir -p out/causal-video/shipped-kernels
gzip -dc examples/causal_video/evidence/kernel-databases/fastvideo-offload.sqlite.gz \
  > out/causal-video/shipped-kernels/fastvideo-offload.sqlite
```

Each adjacent `.report.json.gz` contains its native profiling report: model
settings, source hashes, runtime configuration, and output summary. The
database records measured kernel samples and observed launch inventories;
it contains no model weights or output videos.

- **Inferix:** host KV offload, original streaming decode, metadata adaptation,
  21 latent frames at 480×832, four denoising steps per block.
- **FastVideo:** layerwise DiT offload, metadata and worker-output adaptations,
  81 pixel frames at 480×832, worker intra/inter-op threads both one.

Both profiles used the real pretrained models on A100 GPU1. Native sampling
coverage does not guarantee emulated launch parity: the audits document
cuDNN variants missing from these databases. GPU-resident/optimized variants
need their own matched profiles. See the study's native and partial results
for scope and limitations.
