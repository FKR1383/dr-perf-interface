# General-library regions

This group contains selected statement blocks in 250 distinct Python functions from nine pinned upstream
projects. `generate_cases.py` reproduces snapshots, independent empty-marker
patches, manifests, references, and differential correctness drivers from the
pinned checkouts named in that script.

Each driver imports the marked module from a supplied checkout, asserts its
path is inside that checkout, executes the marked function and its exact hashed
pristine body on fresh bounded inputs, consumes lazy results, compares normalized
values, and requires marker entry. The pristine body uses a copied module
namespace; recursive calls through module globals can resolve the marked symbol,
as recorded in each manifest's coverage note.

Run a project range in isolated hard-linked copies:

```sh
python3 benchmarks/regions/general-libraries/run_sweep.py networkx 1 97 python3
python3 benchmarks/regions/general-libraries/run_sweep.py requests 182 196 \
  /tmp/drperf-gl-venv-misc/bin/python
```

`validation-results.json` records the source identity, region, patch hash, test
asset hashes, status, and evidence for every case. A `region-verified` result is
native correctness and marker-reachability evidence, not a performance result.

Validation environments used during collection are `/tmp/drperf-gl-networkx`
with host Python 3.12, `/tmp/drperf-gl-venv-numpy` and
`/tmp/drperf-gl-venv-pandas` with normally installed builds, and
`/tmp/drperf-gl-venv-urllib3`, `/tmp/drperf-gl-venv-jsonschema`, and
`/tmp/drperf-gl-venv-misc` with editable pinned installs. Checkouts are under
`/tmp/drperf-gl-<project>`.

Recreate the checkouts and the pure-Python editable environments with:

```sh
git clone https://github.com/networkx/networkx /tmp/drperf-gl-networkx
git -C /tmp/drperf-gl-networkx checkout 4e74880b0da01977da79915167c64e5c2af38b47
python3 -m venv /tmp/drperf-gl-venv-networkx
/tmp/drperf-gl-venv-networkx/bin/pip install 'numpy==2.4.4' 'scipy==1.17.1' 'networkx==3.6.1' 'pandas==3.0.2' \
  'requests==2.33.1' 'urllib3==2.0.7' 'attrs==26.1.0' 'packaging==26.1' \
  'cryptography==41.0.7'

# Repeat clone + exact checkout for every REPOS entry in generate_cases.py.
# Pure-Python projects were installed with their runtime dependencies:
python3 -m venv /tmp/drperf-gl-venv-urllib3
python3 -m venv /tmp/drperf-gl-venv-jsonschema
python3 -m venv /tmp/drperf-gl-venv-misc
/tmp/drperf-gl-venv-urllib3/bin/pip install -e /tmp/drperf-gl-urllib3 \
  'pyOpenSSL==26.4.0' 'cryptography==50.0.1'
/tmp/drperf-gl-venv-jsonschema/bin/pip install -e /tmp/drperf-gl-jsonschema \
  'attrs==26.1.0'
/tmp/drperf-gl-venv-misc/bin/pip install -e /tmp/drperf-gl-requests \
  -e /tmp/drperf-gl-packaging -e /tmp/drperf-gl-attrs -e /tmp/drperf-gl-pathspec

git -C /tmp/drperf-gl-numpy submodule update --init --recursive
python3 -m venv /tmp/drperf-gl-venv-numpy
/tmp/drperf-gl-venv-numpy/bin/pip install /tmp/drperf-gl-numpy
python3 -m venv /tmp/drperf-gl-venv-pandas
/tmp/drperf-gl-venv-pandas/bin/pip install /tmp/drperf-gl-pandas \
  'numpy==2.5.3' 'packaging==26.3' 'numba==0.67.0'
```

NumPy requires `git submodule update --init --recursive`. NumPy and pandas use
normal installed binary runtimes because their tests need compiled extensions
and generated files. For those two projects, `run_sweep.py` overlays the exact
hashed Python source snapshot from the pinned revision into an isolated copy of
the installed runtime before applying the marker patch. The receipt therefore
guarantees the tested target Python file is pinned; it does not claim every
compiled extension came from that revision.

`run_sweep.py` writes execution receipts under `validation-executions/`. Each
receipt includes the actual return code, marker-hit JSON, command, source
revision/path/hash, marked-source hash, patch and test hashes, bounded output,
Python version, and installed versions of relevant runtime packages. These
captured versions are the authoritative record for the completed sweep.
