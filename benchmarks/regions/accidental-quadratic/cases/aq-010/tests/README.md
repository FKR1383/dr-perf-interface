# Full-checkout setup

This test needs the pinned Socket CLI tree for sibling modules. Only its
`requests` import is needed by this local file-discovery driver. It was
verified with these setup steps, with `CHECKOUT` set to a new temporary
directory:

```sh
git clone --filter=blob:none --no-checkout https://github.com/SocketDev/socket-python-cli.git "$CHECKOUT"
git -C "$CHECKOUT" checkout 0980358ba9f0d2d3d7cf42af8516fff678931d77
git -C "$CHECKOUT" apply /path/to/aq-010/region.patch
python3 -m venv "$CHECKOUT/.venv"
"$CHECKOUT/.venv/bin/python" -m pip install requests
python3 benchmarks/regions/collect.py test aq-010 --python "$CHECKOUT/.venv/bin/python" --source-root "$CHECKOUT"
```

The test creates only temporary local files and does not call the Socket API.
