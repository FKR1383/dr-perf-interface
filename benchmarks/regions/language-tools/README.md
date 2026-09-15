# Language-tool regions

This collection contains 250 coverage-selected Python regions from eight pinned
symbolic-math, parser, concrete-syntax-tree, template, and compiler projects.
Each case has one empty PerfMark region and a bounded semantic workload with
varied valid inputs, concrete value or round-trip assertions, an exact loaded
source-path assertion, and a required marker hit.

## Reproduce the environment

From the repository root, create an isolated environment and clone the pinned
sources. `validate_all.py` fetches and checks out the full revisions recorded in
the manifests, so the commands do not depend on the upstream default branches.

```sh
python3 -m venv /tmp/ignored_runtime/lt-venv
/tmp/ignored_runtime/lt-venv/bin/pip install coverage pytest
git clone https://github.com/sympy/sympy.git /tmp/ignored_runtime/sympy
git clone https://github.com/tobymao/sqlglot.git /tmp/ignored_runtime/sqlglot
git clone https://github.com/Instagram/LibCST.git /tmp/ignored_runtime/libcst
git clone https://github.com/pylint-dev/astroid.git /tmp/ignored_runtime/astroid
git clone https://github.com/pallets/jinja.git /tmp/ignored_runtime/jinja
git clone https://github.com/pyparsing/pyparsing.git /tmp/ignored_runtime/pyparsing
git clone https://github.com/lark-parser/lark.git /tmp/ignored_runtime/lark
git clone https://github.com/cython/cython.git /tmp/ignored_runtime/cython
git -C /tmp/ignored_runtime/sympy checkout 117eaf45237de39c9d4518a3b7c715f0484ccea9
git -C /tmp/ignored_runtime/sqlglot checkout 3ca824895ef423f7895fb13d72357548c0f1f367
git -C /tmp/ignored_runtime/libcst checkout d9a255843b5cdbecc6834684d233bce1f2987f9d
git -C /tmp/ignored_runtime/astroid checkout 5d1a0a2efabdc43f6cb8449375476b2915ede8fe
git -C /tmp/ignored_runtime/jinja checkout 5ef70112a1ff19c05324ff889dd30405b1002044
git -C /tmp/ignored_runtime/pyparsing checkout efd56db4e59f36b1673ce0eb0823e3afaa9d1201
git -C /tmp/ignored_runtime/lark checkout 9a4fb9c7458e8155636773a3cded0016d52516da
git -C /tmp/ignored_runtime/cython checkout dbbbdbb97f116c46495b5ab88ba0195a277016f9
```

Clone the repositories using the URLs in `validate_all.py`, then install each
checkout editable into the environment:

```sh
/tmp/ignored_runtime/lt-venv/bin/pip install -e /tmp/ignored_runtime/sympy \
  -e /tmp/ignored_runtime/sqlglot -e /tmp/ignored_runtime/libcst \
  -e /tmp/ignored_runtime/astroid -e /tmp/ignored_runtime/jinja \
  -e /tmp/ignored_runtime/pyparsing -e /tmp/ignored_runtime/lark \
  -e /tmp/ignored_runtime/cython
```

## Re-run every isolated case

The runner applies one patch at a time to detached worktrees, invokes the public
collector test command, reverses the patch, and records revision/path/region,
source, patch, test and resource hashes, return code, and observed marker hits.

```sh
/tmp/ignored_runtime/lt-venv/bin/python \
  benchmarks/regions/language-tools/validate_all.py \
  --runtime-root /tmp/ignored_runtime \
  --python /tmp/ignored_runtime/lt-venv/bin/python
```

The checked-in `validation-report.json` is the receipt from the latest complete
run. It also records the Python runtime and full `pip freeze --all` output plus
its SHA-256, so the successful dependency environment is reproducible exactly.
Collection structure and pristine-source identity can be checked separately:

```sh
python3 benchmarks/regions/collect.py check --require-tests
```
