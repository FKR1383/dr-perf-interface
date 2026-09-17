"""Validate the original frozen B-tree interfaces on substantially deeper trees.

All tree construction and PCV replay finish before the first marker, so late
attachment does not instrument millions of setup insertions.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SIZES = (8192, 32768, 131072, 524288)
NAMES = ("depth", "internal_lt", "internal_gt", "internal_eq", "leaf_lt", "leaf_gt")


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
            print(f"Prepared {order} tree with {n:,} keys; depth {rows[-1]['depth']}", flush=True)
    repeats = 256
    for tree, key, row in pending:
        for region, names in (("depth_comparisons", ("depth", "comparisons")), ("audit", ("case_id",))):
            for _ in range(2):
                assert measure(region, tree, key, names, tuple(row[n] for n in names), repeats) == 7*repeats
    Path(destination).write_text(json.dumps(dict(repeats=repeats, cases=rows), indent=2) + "\n")
    print(f"PASS: {len(rows)} cases; {len(rows)*2*2*repeats:,} checked lookups", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
        return
    from validate import describe
    import derive
    import runner
    baseline_path = HERE / "evidence.json"
    baseline = json.loads(baseline_path.read_text())
    # Rebuild the exact same wrapper. Verify the target and checker match the
    # frozen baseline before comparing predictions from that previous run.
    subprocess.run(baseline["build_command"], check=True)
    for name, digest in baseline["hashes"].items():
        assert sha(ROOT / name) == digest, f"Frozen baseline changed: {name}"
    output = Path(tempfile.mkdtemp(prefix="btree-deeper-", dir=ROOT / "out"))
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", str(output / "cases.json")]
    subprocess.run(cmd, check=True)
    native_cases = (output / "cases.json").read_text()
    rc, log, files = runner.run(cmd, str(output / "raw"), timeout=180)
    print(log, flush=True)
    assert rc == 0 and files
    assert (output / "cases.json").read_text() == native_cases
    (output / "instrumented.log").write_text(log)
    runs = runner.load_runs(str(output / "raw"))
    assert not runner.validity(runs), runner.validity(runs)
    keys, slots = runner.blocks_of_set(runs)
    slots = runner.demangle_slots(slots)
    recs = runner.load_traces_all(runs)
    workload = json.loads(native_cases)
    rows, repeats = workload["cases"], workload["repeats"]
    audit, calls, _, nested, dropped = derive.inclusive_vectors(keys, "audit", recs)
    assert not nested and not dropped and len(audit) == len(rows) == 96
    assert all(n == 2 for n in calls.values())
    vectors, calls, names, nested, dropped = derive.inclusive_vectors(keys, "depth_comparisons", recs)
    assert not nested and not dropped and sum(calls.values()) == 2*len(rows)
    deep_refit = describe(vectors, slots, names)
    predictions = {}
    for names in (("depth", "comparisons"), NAMES):
        frozen = baseline["total_fits"][",".join(names)]
        points = []
        for row in rows:
            measured = sum(audit[(row["case_id"],)].values())/repeats
            row["instructions_per_lookup"] = measured
            predicted = frozen["constant"] + sum(a*row[n] for a, n in zip(frozen["coefficients"], names))
            points.append(dict(case_id=row["case_id"], prediction=predicted, measured=measured,
                               relative_error=abs(predicted-measured)/measured))
        predictions[",".join(names)] = dict(coefficients=frozen["coefficients"], constant=frozen["constant"],
            max_relative_error=max(p["relative_error"] for p in points), points=points)
        print("FROZEN", names, "max error", predictions[",".join(names)]["max_relative_error"], flush=True)
    # Diagnostic re-fits ask whether the earlier blockwise rejections persist.
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[n] for n in NAMES), []).append(audit[(row["case_id"],)])
    projected = {v: {b: sum(vec.get(b, 0) for vec in vecs)/len(vecs)
                     for b in set().union(*vecs)} for v, vecs in groups.items()}
    six = describe(projected, slots, NAMES)
    shifted = describe({(v[0]-1,) + v[1:]: vec for v, vec in projected.items()}, slots, ("descents",)+NAMES[1:])
    depths = sorted({r["depth"] for r in rows})
    assert min(depths) >= 4 and max(depths) >= 8, depths
    assert sum(r["depth"] > 4 for r in rows) >= 72
    # Hypothesis under test: the exact semantic interface survives deeper paths.
    assert predictions[",".join(NAMES)]["max_relative_error"] < 1e-9
    assert shifted["max_unexplained"] == 0
    result = dict(recorded_utc=datetime.now(timezone.utc).isoformat(), baseline_sha256=sha(baseline_path),
                  source_sha256=sha(__file__), raw_directory=str(output / "raw"),
                  raw_hashes={p.name: sha(p) for p in sorted((output / "raw").iterdir()) if p.is_file()},
                  tested_depths=depths, frozen_predictions=predictions, workload=workload,
                  deep_refits=dict(two_pcvs=deep_refit, six_pcvs=six, six_shifted=shifted),
                  validation="PASS: deeper-tree correctness, instrumentation, and frozen six-PCV interface")
    text = json.dumps(result, indent=2) + "\n"
    (output / "evidence.json").write_text(text)
    if args.record: (HERE / "deeper-evidence.json").write_text(text)
    print(result["validation"], "depths", depths)
    print("Evidence:", output)


if __name__ == "__main__":
    main()
