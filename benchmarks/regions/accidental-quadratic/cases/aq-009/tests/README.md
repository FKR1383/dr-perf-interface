# Full-checkout setup

This test needs the pinned Black source tree and its declared runtime
dependencies. It was verified with these setup steps, with `CHECKOUT` set to a
new temporary directory:

```sh
git clone --filter=blob:none --no-checkout https://github.com/psf/black.git "$CHECKOUT"
git -C "$CHECKOUT" checkout 3224f36a0fcad002d3aa32f61ab21e14598aded9
git -C "$CHECKOUT" apply /path/to/aq-009/region.patch
python3 -m venv "$CHECKOUT/.venv"
"$CHECKOUT/.venv/bin/python" -m pip install -e "$CHECKOUT"
python3 benchmarks/regions/collect.py test aq-009 --python "$CHECKOUT/.venv/bin/python" --source-root "$CHECKOUT"
```

The editable install creates Black's generated version module while imports
still resolve `linegen.py` from the pinned and patched checkout.
