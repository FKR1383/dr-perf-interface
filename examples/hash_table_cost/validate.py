"""Run hash-table studies against the installed CPython, using real drperf."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import derive
import runner


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_findings(study, reports, cases):
    """Regression assertions for this pinned implementation, not universal claims."""
    if study == "lookup":
        assert reports["lookup_probes"]["max_unexplained"] > .5
        assert reports["lookup_semantic"]["max_unexplained"] > .5
        assert reports["lookup_peeled"]["max_unexplained"] < .001
        assert reports["lookup_peeled"]["max_case_audit_error"] < 1e-6
    elif study == "callback":
        simple, richer = reports["callback_container"], reports["callback_callback"]
        assert simple["same_pcv_cost_spread"][0]["ratio"] > 20
        assert simple["max_unexplained"] < .02
        assert simple["max_case_audit_error"] > 5
        assert richer["max_unexplained"] < .1
        assert richer["max_case_audit_error"] < .1
    else:
        largest = max(cases, key=lambda c:c["rebuild_collisions"])
        assert largest["rebuild_collisions"] > 500*largest["moved"]
        assert reports["insert_moved"]["max_unexplained"] > .5
        assert reports["insert_peeled"]["max_unexplained"] < .25
        # Deliberately do not assert that the final insertion model succeeds.
        # Its reported reconstruction and independent audit errors remain visible.


def analyze(raw, cases):
    runs = runner.load_runs(str(raw))
    assert not runner.validity(runs), runner.validity(runs)
    keys, slots = runner.blocks_of_set(runs)
    slots = runner.demangle_slots(slots)
    recs = runner.load_traces_all(runs)
    reports = {}
    audit_region, = {r["region"] for r in recs if r["region"].endswith("_audit")}
    audit, audit_calls, _, nested, dropped = derive.inclusive_vectors(keys, audit_region, recs)
    assert not nested and not dropped and len(audit) == len(cases)
    for row in cases:
        assert audit_calls[(row["case_id"],)] == 2
        row["measured"] = sum(audit[(row["case_id"],)].values())
    for region in sorted({r["region"] for r in recs if not r["region"].startswith("_perfmark")}):
        vecs, calls, names, nested, dropped = derive.inclusive_vectors(keys, region, recs)
        assert not nested and not dropped
        assert sum(calls.values()) == 2*len(cases), (region, sum(calls.values()))
        if region.endswith("_audit"):
            continue
        model, = derive.derive(vecs, slots, split=False)
        points = []
        for v in model.values:
            total = sum(vecs[v].values())
            remainder = model.irr.get(v, 0)
            points.append(dict(pcvs=v, calls=calls[v], measured=total, predicted=model.formula(v),
                               unexplained=remainder, unexplained_share=remainder/total,
                               reconstruction_error=abs(model.total(v)-total)/total))
        top = sorted(model.by_sym_irr.items(), key=lambda pair: -pair[1])[:10]
        reports[region] = dict(names=names, coefficients=model.a, constant=model.c, dependent=sorted(model.dependent),
                               max_unexplained=max(p["unexplained_share"] for p in points),
                               max_reconstruction_error=max(p["reconstruction_error"] for p in points),
                               points=points, top_unexplained=[dict(module=s[0], function=s[1], mean_cost=v) for s,v in top])
        # These audit regions use case_id solely to keep physically different
        # inputs separate. It is never used as an explanatory PCV.
        checks, groups = [], {}
        for row in cases:
            v = tuple(row[n] for n in names)
            predicted = model.total(v)
            checks.append(dict(case_id=row["case_id"], reconstructed=predicted, measured=row["measured"],
                               relative_error=abs(predicted-row["measured"])/row["measured"]))
            groups.setdefault(v, []).append(row)
        witnesses = []
        for v, rows in groups.items():
            lo, hi = min(rows, key=lambda r:r["measured"]), max(rows, key=lambda r:r["measured"])
            if len(rows) > 1:
                witnesses.append(dict(pcvs=v, low_case=lo["case_id"], high_case=hi["case_id"],
                                      low_cost=lo["measured"], high_cost=hi["measured"], ratio=hi["measured"]/lo["measured"]))
        reports[region].update(case_audit=checks, max_case_audit_error=max(c["relative_error"] for c in checks),
                               same_pcv_cost_spread=sorted(witnesses, key=lambda w:-w["ratio"]))
        print(region, "max unexplained", reports[region]["max_unexplained"], "error", reports[region]["max_reconstruction_error"], flush=True)
        print("  audit: max individual-case error", reports[region]["max_case_audit_error"], flush=True)
        print(" ", derive.formula_text(model, names), flush=True)
    return reports


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", action="store_true")
    p.add_argument("--study", choices=("lookup", "insert", "callback"), default="lookup")
    args = p.parse_args()
    assert platform.python_implementation() == "CPython" and sys.version_info[:2] == (3, 12)
    (HERE / "bin").mkdir(exist_ok=True)
    extension = HERE / "bin" / ("_hash_study"+sysconfig.get_config_var("EXT_SUFFIX"))
    command = ["gcc", "-O2", "-g", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
               "-I"+sysconfig.get_path("include"), str(HERE / "native.c"), "-o", str(extension),
               "-L"+str(ROOT / "build"), "-lperfmark", "-Wl,-rpath,"+str(ROOT / "build")]
    subprocess.run(command, check=True)
    (ROOT / "out").mkdir(exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="hash-table-", dir=ROOT / "out"))
    cmd = [sys.executable, str(HERE / "workload.py"), str(out / "cases.json"), "--study", args.study]
    subprocess.run(cmd, check=True)
    native = (out / "cases.json").read_text()
    rc, log, files = runner.run(cmd, str(out / "raw"), timeout=120)
    print(log, flush=True)
    assert rc == 0 and files
    assert (out / "cases.json").read_text() == native
    (out / "instrumented.log").write_text(log)
    workload = json.loads(native)
    reports = analyze(out / "raw", workload["cases"])
    check_findings(args.study, reports, workload["cases"])
    paths = [HERE / "native.c", HERE / "workload.py", Path(__file__), extension,
             Path(sys.executable).resolve(), ROOT / "lib/derive.py", ROOT / "lib/runner.py",
             ROOT / "build/libdrperf.so", ROOT / "build/libperfmark.so"]
    report = dict(recorded_utc=datetime.now(timezone.utc).isoformat(), python=sys.version, build_command=command,
                  hashes={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p) for p in paths},
                  raw_directory=str(out / "raw"), raw_hashes={p.name: sha(p) for p in (out / "raw").iterdir() if p.is_file()},
                  reports=reports, workload=workload, regression_assertions="passed")
    text = json.dumps(report, indent=2)+"\n"
    (out / "evidence.json").write_text(text)
    if args.record: (HERE / (args.study+"-evidence.json")).write_text(text)
    print("Evidence:", out)


if __name__ == "__main__": main()
