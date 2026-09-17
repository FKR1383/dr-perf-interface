# Preserved Wan timing inputs

These are measured inputs for the fixed workload in [TIMING_STUDY.md](../../TIMING_STUDY.md),
not a general model of A100 performance.

- `gpu-profile.sqlite.gz`: the complete raw A100 PCIe 40GB profile, including
  CUDA function/occupancy queries and the custom `observed_launches` table.
  There are 297 signatures, 2,441 usable timing samples and 359,473 observed
  launches/BLAS operations. No GPU arithmetic runs during timing replay.
- `cpu-profile.txt`: the merged GXVM native instruction/task-clock profile
  collected on an AMD EPYC 7702P, with the patched GX runtime, an 8-CPU container
  quota, and one PyTorch/BLAS thread. Initialization and four warmup steps are
  excluded. It contains 39,515 resolved instruction samples and 8,616 resolved
  task samples, plus 10,617 and 12 unresolved samples. The unresolved
  instruction fraction is 21.18%; this remains a CPU modeling limitation.
  Replay uses 10-us epochs, refund accounting, CPU cost scale 1, and GX's
  existing 30x scaling of stream-worker implementation bookkeeping. That
  worker scaling does not rescale the measured GPU latencies.
- `context-limits.tsv` and `device-attributes.tsv`: native A100 driver queries
  used by the opt-in cuDNN host-dispatch overlay. Columns are query ID, return
  status, and value. A nonzero status means the value must not be treated as a
  successful device query.
- `kernel-libraries.json`: SHA-256 fingerprints of the fifteen matching native
  and emulated framework/CUDA libraries, including FlashAttention.
- `manifest.json`: compressed and uncompressed hashes and source-artifact paths.

Unpack and verify with:

```bash
python3 examples/wan_gx/unpack_timing_inputs.py out/wan-timing/inputs
```

Use `gpu-profile.sqlite` for `--gpu-db` and `cpu-profile.txt` for `--cpu-db`.
The GPU database is required for function-query replay even in plain/drperf
mode. Those modes still do not enable GPU timing waits. A different framework
build, kernel signature, CPU host or workload requires new matching evidence;
the databases do not establish coverage or accuracy by their presence alone.
