# Full-checkout setup

This test needs the pinned Cython source tree so `ModuleNode.py` can import its
sibling compiler modules. It was verified with these setup steps, with
`CHECKOUT` set to a new temporary directory:

```sh
git clone --filter=blob:none --no-checkout https://github.com/cython/cython.git "$CHECKOUT"
git -C "$CHECKOUT" checkout 1b028d34d6a3ec82f4687df1e0db598721c7a695
git -C "$CHECKOUT" apply /path/to/aq-002/region.patch
python3 -m venv "$CHECKOUT/.venv"
python3 benchmarks/regions/collect.py test aq-002 --python "$CHECKOUT/.venv/bin/python" --source-root "$CHECKOUT"
```

No additional Python packages are required for this bounded driver.
