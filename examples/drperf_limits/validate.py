"""Execute real native programs and check drperf's failure/repair behavior."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import derive
import runner


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="update checked-in evidence after validation")
    args = parser.parse_args()
    binary = HERE / "bin" / "programs"
    binary.parent.mkdir(exist_ok=True)
    command = ["gcc", "-O2", "-g", "-Wall", "-Wextra", "-Werror",
               "-fno-tree-vectorize", "-fno-unroll-loops", str(HERE / "programs.c"),
               "-o", str(binary), "-L" + str(ROOT / "build"), "-lperfmark",
               "-Wl,-rpath," + str(ROOT / "build")]
    subprocess.run(command, check=True)
    native = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    print(native.stdout.strip(), flush=True)
    (ROOT / "out").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="drperf-limits-", dir=ROOT / "out"))
    raw = output / "raw"
    rc, log, files = runner.run([str(binary)], str(raw), timeout=120)
    (output / "run.log").write_text(log)
    assert rc == 0 and files, log
    runs = runner.load_runs(str(raw))
    assert not runner.validity(runs), runner.validity(runs)
    keys, slots = runner.blocks_of_set(runs)
    slots = runner.demangle_slots(slots)
    recs = runner.load_traces_all(runs)
    regions = sorted({r["region"] for r in recs if not r["region"].startswith("_perfmark")})
    expected_calls = {
        "product_raw": 48, "product_fixed": 48, "clamp_raw": 48, "clamp_fixed": 48,
        "correlation_grid_raw": 48, "correlation_fixed": 48,
        "correlation_train": 12, "correlation_train_dependent": 12,
        "data_averaged": 36, "data_fixed": 36, "data_light": 12, "data_heavy": 12,
        "threshold_train": 15, "threshold_holdout": 12, "threshold_all_raw": 27,
        "threshold_fixed": 27, "tolerance_raw": 15, "tolerance_fixed": 15,
    }
    assert set(regions) == set(expected_calls), regions
    models, report = {}, {}
    for name in regions:
        vecs, calls, names, nested, dropped = derive.inclusive_vectors(keys, name, recs)
        assert not nested and not dropped
        assert sum(calls.values()) == expected_calls[name], (name, calls)
        fitted = derive.derive(vecs, slots, split=False)
        assert len(fitted) == 1, (name, len(vecs))
        model = models[name] = fitted[0]
        points = []
        for v in model.values:
            counted = sum(y for b, y in vecs[v].items() if not derive.is_runtime(slots.get(b, ("?", "?"))))
            unexplained = model.irr.get(v, 0)
            prediction = model.formula(v)
            points.append(dict(pcvs=list(v), calls=calls[v], measured=counted,
                               formula=prediction, unexplained=unexplained,
                               unexplained_share=unexplained / counted,
                               # Reconstruction adds the explicitly reported remainder.
                               reconstruction_error_share=abs(prediction + unexplained - counted) / counted))
        max_share = max(p["unexplained_share"] for p in points)
        max_error = max(p["reconstruction_error_share"] for p in points)
        report[name] = dict(names=names, coefficients=model.a, constant=model.c,
                            dependent_columns=sorted(model.dependent),
                            observed_unexplained_gate_pass=max_share <= .05,
                            max_unexplained_share=max_share,
                            max_reconstruction_error_share=max_error, points=points)
        print(f"{name:29s} unexplained={max_share:8.2%} reconstruction_error={max_error:8.2%} "
              f"{derive.formula_text(model, names)}", flush=True)

    # These assertions check failure/repair distinctions, not compiler-specific coefficients.
    for stem in ("product", "clamp", "threshold_all"):
        assert report[stem + "_raw"]["max_unexplained_share"] > .05, stem
    for name in ("product_fixed", "clamp_fixed", "data_fixed", "correlation_fixed",
                 "threshold_fixed", "tolerance_fixed"):
        assert report[name]["observed_unexplained_gate_pass"], name
        assert report[name]["max_reconstruction_error_share"] < .05, name
    assert report["data_averaged"]["observed_unexplained_gate_pass"]
    light = {tuple(p["pcvs"]): p["measured"] for p in report["data_light"]["points"]}
    heavy = {tuple(p["pcvs"]): p["measured"] for p in report["data_heavy"]["points"]}
    variation = [{"n": v[0], "light_instructions": light[v], "heavy_instructions": heavy[v],
                  "heavy_over_light": heavy[v] / light[v]} for v in sorted(light)]
    assert min(p["heavy_over_light"] for p in variation) > 3
    assert report["correlation_train"]["observed_unexplained_gate_pass"]
    assert report["correlation_grid_raw"]["observed_unexplained_gate_pass"]
    assert report["correlation_train_dependent"]["dependent_columns"]
    # Freeze the diagonal-trained n formula. Do NOT refit on the independent grid.
    correlation_holdout = []
    for n in (128, 256, 512, 1024):
        for p in report["correlation_fixed"]["points"]:
            actual, m = p["measured"], p["pcvs"][0]
            prediction = models["correlation_train"].formula((n,))
            correlation_holdout.append(dict(n=n, m=m, prediction=prediction, measured=actual,
                                             relative_error=abs(prediction - actual) / actual))
    assert max(p["relative_error"] for p in correlation_holdout) > 1
    assert report["threshold_train"]["observed_unexplained_gate_pass"]
    threshold_holdout = []
    for p in report["threshold_holdout"]["points"]:
        actual = p["measured"]
        prediction = models["threshold_train"].formula(p["pcvs"])
        threshold_holdout.append(dict(n=p["pcvs"][0], prediction=prediction, measured=actual,
                                       relative_error=abs(prediction - actual) / actual))
    assert min(p["relative_error"] for p in threshold_holdout) > .9
    assert report["tolerance_raw"]["observed_unexplained_gate_pass"]
    assert report["tolerance_raw"]["max_reconstruction_error_share"] > .1

    evidence = dict(
        recorded_utc=datetime.now(timezone.utc).isoformat(),
        scope="Observed mean user-space instruction counts; no universal or elapsed-time claim.",
        platform=platform.platform(), compiler=subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
        build_command=command, native_stdout=native.stdout, instrumented_stdout=log,
        derive_settings=dict(relative_tolerance=derive.REL_TOL, absolute_tolerance=derive.ABS_TOL,
                             automatic_regime_splitting=False, unexplained_gate=.05),
        hashes={str(p.relative_to(ROOT)): sha(p) for p in
                (HERE / "programs.c", HERE / "validate.py", binary, ROOT / "lib/derive.py",
                 ROOT / "lib/runner.py", ROOT / "build/libdrperf.so", ROOT / "build/libperfmark.so",
                 ROOT / "build/libdrperf_attach.so", ROOT / "third_party/dynamorio/bin64/drrun")},
        raw_directory=str(raw), raw_hashes={p.name: sha(p) for p in sorted(raw.iterdir()) if p.is_file()},
        regions=report, same_length_variation=variation, correlation_frozen_holdout=correlation_holdout,
        threshold_frozen_holdout=threshold_holdout,
        validation="PASS: all correctness, instrumentation, counterexample, and repair assertions")
    text = json.dumps(evidence, indent=2) + "\n"
    (output / "evidence.json").write_text(text)
    if args.record:
        (HERE / "evidence.json").write_text(text)
    print(evidence["validation"])
    print("Full measurements:", output)


if __name__ == "__main__":
    main()
