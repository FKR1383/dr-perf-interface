"""Validate the fixed checker with six PCVs through the ordinary C marker.

Unlike the historical studies, this does not re-project audit counts onto
PCVs offline: all six are declared to perfmark_begin_v at region entry.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import sysconfig
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEPTH_NAMES = ("depth", "internal_lt", "internal_gt", "internal_eq", "leaf_lt", "leaf_gt")
DESCENT_NAMES = ("descents",) + DEPTH_NAMES[1:]
SIZES = (128, 512, 8192, 131072, 524288)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def worker(destination):
    from workload import SmallNodes, path_summary, measure
    pending, rows = [], []
    for n in SIZES:
        for order in ("ascending", "descending", "shuffled"):
            tree = SmallNodes()
            indices = list(range(n))
            if order == "descending": indices.reverse()
            if order == "shuffled": random.Random(1729).shuffle(indices)
            for i in indices: tree[1000+2*i] = 7
            tree._check()
            for rank in sorted({0, 1, n//8, n//4, n//2, 3*n//4, n-2, n-1}):
                key = 1000+2*rank
                counts, path, leaf = path_summary(tree, key)
                row = dict(case_id=len(rows), n=n, rank=rank, key=key, order=order,
                           **counts, path=path, leaf=leaf)
                rows.append(row)
                pending.append((tree, key, row))
    for tree, key, row in pending:
        for region, names in (("six_depth", DEPTH_NAMES), ("six_descents", DESCENT_NAMES), ("audit", ("case_id",))):
            for _ in range(2):
                assert measure(region, tree, key, names, tuple(row[n] for n in names), 256) == 7*256
    Path(destination).write_text(json.dumps(dict(repeats=256, cases=rows), indent=2) + "\n")
    print(f"PASS: {len(rows)} cases; {len(rows)*3*2*256:,} checked lookups", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
        return
    from importlib.metadata import version
    import BTrees._IIBTree
    assert version("BTrees") == "6.1"
    sys.path.insert(0, str(ROOT / "lib"))
    import derive
    import runner
    binary_dir = HERE / "bin"
    binary_dir.mkdir(exist_ok=True)
    extension = binary_dir / ("_btree_measure" + sysconfig.get_config_var("EXT_SUFFIX"))
    command = ["gcc", "-O2", "-g", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
               "-I" + sysconfig.get_path("include"), str(HERE / "measure.c"), "-o", str(extension),
               "-L" + str(ROOT / "build"), "-lperfmark", "-Wl,-rpath," + str(ROOT / "build")]
    subprocess.run(command, check=True)
    (ROOT / "out").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="btree-fixed-", dir=ROOT / "out"))
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", str(output / "cases.json")]
    subprocess.run(cmd, check=True)
    native = (output / "cases.json").read_text()
    rc, log, files = runner.run(cmd, str(output / "raw"), timeout=180)
    assert rc == 0 and files, log
    assert (output / "cases.json").read_text() == native
    (output / "instrumented.log").write_text(log)
    runs = runner.load_runs(str(output / "raw"))
    assert not runner.validity(runs), runner.validity(runs)
    keys, slots = runner.blocks_of_set(runs)
    slots = runner.demangle_slots(slots)
    recs = runner.load_traces_all(runs)
    workload = json.loads(native)
    rows = workload["cases"]
    assert len(rows) == 120 and max(r["depth"] for r in rows) >= 8
    results, models = {}, {}
    for region, expected_names in (("six_depth", DEPTH_NAMES), ("six_descents", DESCENT_NAMES)):
        vecs, calls, names, nested, dropped = derive.inclusive_vectors(keys, region, recs)
        assert tuple(names) == expected_names, names
        assert not nested and not dropped and sum(calls.values()) == 2*len(rows)
        assert all(r["nk"] == 6 for r in recs if r["region"] == region)
        model, = derive.derive(vecs, slots, split=False)
        models[region] = model
        assert model.n_irr == 0 and not model.dependent
        points = []
        for v in model.values:
            measured = sum(vecs[v].values())
            error = abs(model.formula(v)-measured)/measured
            assert error < 1e-9
            points.append(dict(pcvs=v, calls=calls[v], measured=measured, prediction=model.formula(v),
                               relative_error=error, unexplained=model.irr.get(v, 0)))
        results[region] = dict(names=names, coefficients=model.a, constant=model.c,
                               max_relative_error=max(p["relative_error"] for p in points),
                               unexplained_blocks=model.n_irr, points=points)
        print(region, derive.formula_text(model, names), "unexplained=0", flush=True)
    audit, calls, _, nested, dropped = derive.inclusive_vectors(keys, "audit", recs)
    assert len(audit) == len(rows) and not nested and not dropped and sum(calls.values()) == 2*len(rows)
    # Validate each physical tree/query separately, not just feature-state means.
    for row in rows:
        counted = sum(audit[(row["case_id"],)].values())
        first = models["six_depth"].formula(tuple(row[n] for n in DEPTH_NAMES))
        second = models["six_descents"].formula(tuple(row[n] for n in DESCENT_NAMES))
        assert abs(first-counted)/counted < 1e-9
        assert abs(second-counted)/counted < 1e-9
        row["measured_per_lookup"] = counted/256
    paths = [Path(__file__), HERE / "measure.c", HERE / "workload.py", extension,
             Path(BTrees._IIBTree.__file__), ROOT / "lib/derive.py", ROOT / "lib/runner.py",
             ROOT / "client/drperf.c", ROOT / "build/libdrperf.so", ROOT / "build/libperfmark.so"]
    evidence = dict(recorded_utc=datetime.now(timezone.utc).isoformat(), build_command=command,
                    python=sys.version, dependencies=subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True),
                    hashes={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p) for p in paths},
                    raw_directory=str(output / "raw"), raw_hashes={p.name: sha(p) for p in (output / "raw").iterdir() if p.is_file()},
                    results=results, workload=workload,
                    validation="PASS: six actual marker PCVs, zero unexplained blocks, and equivalent depth/descents interfaces")
    text = json.dumps(evidence, indent=2) + "\n"
    (output / "evidence.json").write_text(text)
    if args.record: (HERE / "fixed-evidence.json").write_text(text)
    print(evidence["validation"])
    print("Evidence:", output)


if __name__ == "__main__":
    main()
