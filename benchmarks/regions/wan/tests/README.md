# Wan correctness and reachability tests

Each case contains a bounded CPU test for its patched Diffusers source region. Exported tests receive `helper.py` and `marker_probe.py` through the manifest's `tests.resources` entries.

Run the manifest command from the exported case directory, replacing `{python}` with a Python environment containing PyTorch, Diffusers runtime dependencies, Transformers, and Pillow, and replacing `{source_root}` with the root of the patched Diffusers checkout. The helper prepends `{source_root}/src` and verifies that `diffusers` was loaded from that location.

The tests use random tiny Wan models and fixed seeds. Every case runs three distinct small configurations, varying the relevant batch, spatial, temporal, sequence, schedule, or blend inputs. They assert exact shapes where the public operation defines them, finite tensor values, and operation-specific semantics. `Probe.finish()` also requires the case marker to have been entered. Without `DRPERF`, the probe records native correctness and reachability; with `DRPERF`, it delegates marker calls to the real PerfMark implementation as well.
