#!/usr/bin/env python3
"""Measure both selected feature sets without further agent feedback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from evaluation import drperf_measure as measurement
from evaluation.results import read_json, variables, write_json


def load_vectors(raw):
    runner, derive = measurement.runner, measurement.derive
    runs = runner.load_runs(str(raw))
    warnings = runner.validity(runs)
    if warnings:
        raise ValueError("; ".join(warnings))
    keys, slots = runner.blocks_of_set(runs)
    traces = runner.load_traces_all(runs)
    vecs, calls, names, nested, dropped = derive.inclusive_vectors(keys, "compress", traces)
    if dropped or nested:
        raise ValueError("validation expects complete, non-nested compression measurements")
    inside, _ = runner.marker_cost(runs)
    return vecs, calls, names, slots, inside


def frozen_predictions(discovery_raw, validation_raw):
    train, _, names, slots, calibration = load_vectors(discovery_raw)
    test, calls, test_names, _, test_calibration = load_vectors(validation_raw)
    if names != test_names:
        raise ValueError("feature order changed between measurements")
    regimes = measurement.derive.derive(train, slots)
    for regime in regimes:
        regime.c -= calibration
    rows = []
    for values, vector in sorted(test.items()):
        if len(regimes) == 1:
            regime = regimes[0]
        elif len(regimes) == 2 and values[0] <= regimes[0].values[-1][0]:
            regime = regimes[0]
        elif len(regimes) == 2 and values[0] >= regimes[1].values[0][0]:
            regime = regimes[1]
        else:
            regime = None  # No invented boundary in a gap between training regimes.
        actual = sum(vector.values()) - test_calibration
        rows.append({"states": dict(zip(names, values)), "calls": calls[values],
                     "actual_mean_instructions": actual,
                     "predicted_instructions": regime.formula(values) if regime else None})
    predicted = [r for r in rows if r["predicted_instructions"] is not None]
    numerator = sum(abs(r["predicted_instructions"] - r["actual_mean_instructions"]) * r["calls"]
                    for r in predicted)
    denominator = sum(r["actual_mean_instructions"] * r["calls"] for r in predicted)
    return {"description": "Frozen discovery formula versus validation state means; no refitting. "
                           "The formula excludes discovery irregular cost. Same-state calls are averaged.",
            "weighted_absolute_percentage_error": numerator / denominator if denominator else None,
            "predicted_calls": sum(r["calls"] for r in predicted),
            "total_calls": sum(calls.values()), "points": rows}


def instrument(workspace, names):
    if len(names) > 4:
        raise ValueError("the selected answer exceeds the four-state measurement limit")
    if "input" in names:
        raise ValueError("'input' is a byte-buffer pointer, not an integer feature describing its contents. "
                         "The static answer cannot be measured as returned; no pointer-address proxy was substituted.")
    if any(re.search(r"[;{}\n\r]", name) for name in names):
        raise ValueError("expected C expressions, not C statements")
    path = workspace / "driver.c"
    text = path.read_text()
    # Expose the existing stream fields when an answer refers to internal state.
    # This header supplies declarations only; it does not compute new features.
    text = text.replace('#include "zlib.h"\n', '#include "zlib.h"\n#include "deflate.h"\n')
    if names:
        declarations = (
            "\n    ".join(f'_Static_assert(__builtin_classify_type({n}) == 1, "state must be an integer");'
                          for n in names) + "\n    " +
            "const char *evaluation_names[] = {" + ", ".join(json.dumps(n) for n in names) + "};\n"
            "    int64_t evaluation_values[] = {" + ", ".join(f"(int64_t)({n})" for n in names) + "};\n"
            f'    perfmark_begin_v("compress", {len(names)}, evaluation_names, evaluation_values);')
    else:
        declarations = 'perfmark_begin_v("compress", 0, NULL, NULL);'
    text, count = re.subn(r"(/\* EVALUATION_STATES_BEGIN \*/).*?(/\* EVALUATION_STATES_END \*/)",
                         lambda m: m[1] + "\n    " + declarations + "\n    " + m[2], text, flags=re.S)
    if count != 1:
        raise ValueError("cannot locate the original instrumentation boundary")
    path.write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "build/evaluation-zlib")
    parser.add_argument("--validation-dir", type=Path, default=ROOT / "build/evaluation-zlib-validation")
    parser.add_argument("--results", type=Path, required=True, help="discovery result.json")
    parser.add_argument("--out", type=Path, required=True, help="new directory for validation evidence")
    args = parser.parse_args()
    workspace, validation, out = args.workspace.resolve(), args.validation_dir.resolve(), args.out.resolve()
    if out.exists():
        parser.error("validation output directory must not already exist")
    if out == workspace or workspace in out.parents or out == validation or validation in out.parents:
        parser.error("validation output must be outside both input directories")
    provenance = read_json(validation / "provenance.json")
    for base, files in ((workspace, provenance["discovery"]["files"]),
                        (validation, provenance["validation"]["files"]),
                        (workspace, {"driver.c": provenance["driver_sha256"]})):
        for name, expected in files.items():
            if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
                parser.error(f"frozen input changed: {base / name}")
    answer = read_json(args.results)
    candidates = {"agent_only": variables(answer["agent_only"]["variables"]),
                  "agent_drperf": variables(answer["agent_drperf"]["selected_variables"])}
    out.mkdir(parents=True)
    report = {"candidates": {}, "provenance": provenance,
              "note": "Validation irregularity refits coefficients using fixed selected features. "
                      "Frozen prediction error uses a replay of the discovery workload and is reported "
                      "separately. No feedback is sent to agents."}
    original_cwd = Path.cwd()
    for label, names in candidates.items():
        destination = out / label
        destination.mkdir()
        record = {"variables": names}
        report["candidates"][label] = record
        print(f"Validating {label}: {names}", flush=True)
        with tempfile.TemporaryDirectory(prefix="drperf-zlib-validation-") as temp:
            target = Path(temp) / "workspace"
            shutil.copytree(workspace, target)
            try:
                instrument(target, names)
                built = subprocess.run(["./build.sh"], cwd=target, text=True, capture_output=True)
                (destination / "build.log").write_text(built.stdout + built.stderr)
                shutil.copyfile(target / "driver.c", destination / "driver.c")
                if built.returncode:
                    raise ValueError("selected expressions do not compile at the original boundary; see build.log")
                os.chdir(target)
                for phase in ("discovery", "validation"):
                    if phase == "validation":
                        shutil.rmtree(target / "inputs")
                        shutil.copytree(validation / "inputs", target / "inputs")
                        shutil.copyfile(validation / "workloads/validation.tsv", target / "workloads/validation.tsv")
                    artifact = destination / phase
                    artifact.mkdir()
                    record[phase] = measurement.measure(["./program", f"workloads/{phase}.tsv"],
                                                         artifact, "compress", names)
                    write_json(artifact / "measurement.json", record[phase])
                if all(record[p]["status"] == "ok" for p in ("discovery", "validation")):
                    record["frozen_predictions"] = frozen_predictions(destination / "discovery/raw",
                                                                       destination / "validation/raw")
            except (ValueError, OSError) as exc:
                record["error"] = str(exc)
            finally:
                os.chdir(original_cwd)
                write_json(out / "validation.json", report)
    print(f"Validation report: {out / 'validation.json'}")
    return int(any("error" in r or any(r.get(p, {}).get("status") != "ok"
               for p in ("discovery", "validation")) for r in report["candidates"].values()))


if __name__ == "__main__":
    sys.exit(main())
