"""Parse a real corpus with a given libcst build and digest every tree.

Run once per build; the digests must match exactly. `repr(module)` is libcst's
full structural representation, so equal digests mean identical CSTs, not just
identical round-tripped source.
"""
import hashlib, json, pathlib, sys


def main():
    repo = pathlib.Path(sys.argv[1])          # a libcst checkout with its native .so in place
    out = pathlib.Path(sys.argv[2])
    sys.path.insert(0, str(repo))
    import libcst

    corpus = []
    for root in sys.argv[3:]:
        corpus.extend(sorted(pathlib.Path(root).rglob("*.py")))

    results = {}
    roundtrip_ok = 0
    failed = []
    for path in corpus:
        try:
            src = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        try:
            module = libcst.parse_module(src)
        except Exception as exc:
            failed.append((str(path), type(exc).__name__))
            continue
        if module.code == src:
            roundtrip_ok += 1
        results[str(path)] = hashlib.sha256(repr(module).encode()).hexdigest()[:16]

    out.write_text(json.dumps({"digests": results, "roundtrip_ok": roundtrip_ok,
                               "failed": failed, "n": len(results)}, indent=1))
    print(f"{len(results)} files parsed, {roundtrip_ok} round-tripped exactly, "
          f"{len(failed)} failed to parse")
    print("corpus digest:", hashlib.sha256(
        json.dumps(results, sort_keys=True).encode()).hexdigest()[:16])


if __name__ == "__main__":
    main()
