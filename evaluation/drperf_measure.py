#!/usr/bin/env python3
"""Evaluation-only adapter to runner/derive; no variable selection lives here."""
import argparse
import contextlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))
import derive  # noqa: E402
import runner  # noqa: E402

try:
    from .results import MAX_ATTEMPTS, EvaluationError, read_json, variables, write_json
except ImportError:
    from results import MAX_ATTEMPTS, EvaluationError, read_json, variables, write_json


def check_build():
    if not all(Path(p).is_file() for p in
               (runner.DRRUN, runner.CLIENT, runner.ATTACH, runner.PERFMARK)):
        raise EvaluationError(f"Dr. Perf has not been built; run {ROOT / 'build.sh'}")


def failed(status, message, **details):
    return {"formula": None, "irregularity": None, "status": status,
            "details": {"message": message, **details}}


def analyze(out, region, expected):
    try:
        return _analyze(out, region, expected)
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return failed("measurement_error", str(exc))


def _analyze(out, region, expected):
    rs = runner.load_runs(str(out))
    warnings = runner.validity(rs)
    if warnings:
        return failed("invalid_measurement", "; ".join(warnings))
    keys, slots = runner.blocks_of_set(rs)
    if not any(k["region"] == region and k["count"] > 0 for k in keys.values()):
        return failed("region_not_reached", f"target region {region!r} was not reached")
    recs = [r for r in runner.load_traces_all(rs) if not r["region"].startswith(runner.CALIB)]
    vecs, trig, names, nested, dropped = derive.inclusive_vectors(keys, region, recs)
    if dropped:
        return failed("invalid_measurement", f"{dropped} calls could not be modelled")
    # A candidate label must really have been declared in the measured binary.
    # Reject inconsistent declarations too (per_state groups only by values).
    declarations = {tuple(n for n, _ in k["states"]) for k in keys.values()
                    if k["region"] == region and k["count"] > 0}
    if sorted(names) != expected or len(declarations) != 1:
        return failed("state_mismatch", "measured state names differ from candidate variables",
                      declared_states=list(names))
    regimes = derive.derive(vecs, slots)
    if not regimes:
        return failed("insufficient_state_variation",
                      f"no model: {len(vecs)} state points; need at least "
                      f"{max(derive.MIN_VALUES, len(names) + 2)}",
                      state_points=len(vecs), calls=sum(trig.values()))
    inside, outside = runner.marker_cost(rs)
    parts, details, total, irregular = [], [], 0.0, 0.0
    unexplained = {}
    for r in regimes:
        # Same calibration and order as bin/drperf.cost_lines, before irr_share.
        r.c -= inside + nested * (inside + outside)
        share = r.irr_share()
        if not math.isfinite(share) or not 0 <= share <= 1:
            return failed("invalid_measurement", "calibrated irregularity is outside [0, 1]")
        formula = derive.formula_text(r, names)
        condition = derive.regime_range(regimes, r, names)
        parts.append(f"{condition}: {formula}" if len(regimes) > 1 else formula)
        details.append({"condition": condition, "formula": formula, "irregularity": share,
                        "state_points": len(r.values),
                        "fixed_states": [n for j, n in enumerate(names)
                                         if len({v[j] for v in r.values}) == 1],
                        "dependent_states": [names[j] for j in sorted(r.dependent)]})
        total += sum(r.total(v) for v in r.values)
        irregular += sum(r.irr.values())
        for (module, function), cost in r.by_sym_irr.items():
            key = (module, function)
            unexplained[key] = unexplained.get(key, 0.0) + cost * len(r.values)
    # One regime uses irr_share verbatim. Multiple regimes use the same ratio
    # across their disjoint state points, NOT an unweighted mean of percentages.
    share = details[0]["irregularity"] if len(regimes) == 1 else (irregular / total if total else 0.0)
    if not math.isfinite(share) or not 0 <= share <= 1:
        return failed("invalid_measurement", "combined irregularity is outside [0, 1]")
    return {"formula": "; ".join(parts), "irregularity": share, "status": "ok",
            "details": {"regimes": details, "calls": sum(trig.values()),
                        "unexplained_functions": [
                            {"module": module, "function": function,
                             "share_of_total_cost": cost / total if total else 0.0}
                            for (module, function), cost in
                            sorted(unexplained.items(), key=lambda pair: pair[1], reverse=True)[:5]],
                        "excluded_nested_regions": derive.nested_calls(recs, region)}}


def measure(command, out, region, expected):
    try:
        check_build()
    except EvaluationError as exc:
        return failed("drperf_not_built", str(exc))
    try:
        rc, output, files = runner.run(command, str(out / "raw"))
        (out / "workload.log").write_text(output)
        write_json(out / "process.json", {"returncode": rc})
        if rc != 0:
            return failed("workload_failed", f"workload exited with status {rc}; see workload.log")
        if not files:
            return failed("region_not_reached", f"no measurements: region {region!r} was not reached")
        return analyze(out / "raw", region, expected)
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return failed("measurement_error", str(exc))


def attempt(config, candidate):
    candidate = variables(candidate)
    if len(candidate) > 4:
        raise EvaluationError("perfmark supports at most four declared states")
    if Path.cwd().resolve() != Path(config["workspace"]).resolve():
        raise EvaluationError("measurement must run in the disposable workspace")
    journal = Path(config["journal"])
    journal.mkdir(exist_ok=True)
    index = len(list(journal.glob("attempt-*"))) + 1
    if index > min(config["max_attempts"], MAX_ATTEMPTS):
        raise EvaluationError("experiment limit reached")
    for path in journal.glob("attempt-*/measurement.json"):
        previous = read_json(path)
        if previous["status"] == "ok" and variables(previous["variables"]) == candidate:
            raise EvaluationError("this variable set was already measured successfully; test a new set")
    out = journal / f"attempt-{index:03d}"
    out.mkdir()  # Never overwrite an existing experiment.
    write_json(out / "request.json", {"variables": candidate})
    result = {"attempt": index, "variables": candidate,
              **measure(config["command"], out, config["region"], candidate)}
    write_json(out / "measurement.json", result)
    return result


def recorded_attempts(config):
    """Re-analyze raw measurements instead of trusting agent numbers."""
    try:
        return _recorded_attempts(config)
    except (KeyError, TypeError) as exc:
        raise EvaluationError(f"malformed measurement journal: {exc}") from exc


def _recorded_attempts(config):
    records = []
    for index, out in enumerate(sorted(Path(config["journal"]).glob("attempt-*")), 1):
        if out.name != f"attempt-{index:03d}" or index > min(config["max_attempts"], MAX_ATTEMPTS):
            raise EvaluationError("invalid measurement journal sequence or experiment limit")
        record = read_json(out / "measurement.json")
        candidate = variables(read_json(out / "request.json")["variables"])
        if record["attempt"] != index or record["variables"] != candidate:
            raise EvaluationError("measurement record does not match its request")
        if (out / "process.json").exists():
            rc = read_json(out / "process.json")["returncode"]
            measured = (analyze(out / "raw", config["region"], candidate) if rc == 0 else
                        failed("workload_failed", f"workload exited with status {rc}"))
            if any(record[k] != measured[k] for k in ("formula", "irregularity", "status")):
                raise EvaluationError("measurement record does not match Dr. Perf raw data")
        elif record["status"] not in ("measurement_error", "drperf_not_built"):
            raise EvaluationError("measurement record is missing the workload exit status")
        records.append({k: record[k] for k in
                        ("attempt", "variables", "formula", "irregularity", "status")})
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--variables-json", required=True)
    args = parser.parse_args(argv)
    try:
        # Keep all runner diagnostics off the machine-readable stdout channel.
        with contextlib.redirect_stdout(sys.stderr):
            result = attempt(read_json(args.config), json.loads(args.variables_json))
        print(json.dumps(result, allow_nan=False))
        return 0 if result["status"] == "ok" else 1
    except (EvaluationError, OSError, ValueError) as exc:
        print(f"measurement: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
