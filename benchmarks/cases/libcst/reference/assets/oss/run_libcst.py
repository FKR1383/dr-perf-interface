"""Parse one deeply left-nested Python expression with libcst, for drperf.

Usage: run_libcst.py [n_terms=N] [shape=0|1|2]

shape 0: a0 + a1 + ... + aN      (binary operator chain)
shape 1: T0 | T1 | ... | TN      (type union, same shape)
shape 2: obj.m0().m1()...        (method call chain)

The expression is built once, outside the region, so the region is the parse only.
"""
import sys

sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")
import perfmark


def build(shape, n):
    if shape == 1:
        return "x: " + " | ".join(f"T{i}" for i in range(n)) + " = None\n"
    if shape == 2:
        return "x = obj" + "".join(f".m{i}()" for i in range(n)) + "\n"
    return "x = " + " + ".join(f"a{i}" for i in range(n)) + "\n"


def main():
    args = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            args[k] = int(v)
    n = args.get("n_terms", 200)
    shape = args.get("shape", 0)

    import libcst

    src = build(shape, n)
    with perfmark.region("parse_module", n_terms=n, n_terms_sq=n * n):
        module = libcst.parse_module(src)

    print(f"n_terms={n} shape={shape} chars={len(src)} ok={module is not None}")


if __name__ == "__main__":
    main()
