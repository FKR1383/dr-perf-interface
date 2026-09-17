#!/usr/bin/env python3
"""Validate and summarize measured drperf basic-block counts for causal video.

Input is a managed run directory containing drperf/raw, or the raw directory.
Writes JSON, Markdown, and TSV next to the requested output prefix. An invalid
collection exits 2 and never emits a performance summary.
"""

import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
import derive
import runner


def formatted(number):
    return f"{number:,.0f}" if number is not None else "—"


def top_functions(counts, limit=8):
    return [{"module": module, "symbol": symbol, "instructions": round(value)}
            for (module, symbol), value in counts.most_common(limit)]


def summarize(path):
    raw = path / "drperf" / "raw" if (path / "drperf" / "raw").is_dir() else path
    if not raw.is_dir():
        raise ValueError(f"drperf raw directory missing: {raw}")
    run_set = runner.load_runs(str(raw))
    if not run_set["runs"]:
        raise ValueError("no completed drperf records")
    errors = runner.validity(run_set)
    counters = [run["data"].get("drperf", {}) for run in run_set["runs"]]
    for counter in counters:
        pid = counter.get("pid", "unknown")
        if not counter.get("marker_seen"):
            errors.append(f"PID {pid}: no marker was observed")
        if counter.get("depth_overflows"):
            errors.append(f"PID {pid}: {counter['depth_overflows']} marker depth overflows")
    if errors:
        raise ValueError("invalid drperf collection:\n - " + "\n - ".join(sorted(set(errors))))
    keys, slots = runner.blocks_of_set(run_set)
    if not keys or not slots:
        errors.append("basic-block keys or slots missing")
    setup_regions = {"fastvideo_attach_setup"}
    names = sorted({key["region"] for key in keys.values()
                    if key["region"] not in setup_regions
                    and not key["region"].startswith("_perfmark")
                    and not runner.is_structural(key["region"])})
    if not names:
        errors.append("no measured application regions")
    prepared = {}
    for name in names:
        states, pcvs, dropped = derive.per_state(keys, name)
        vecs, calls = derive.per_trigger(states)
        total = sum(sum(vec.values()) * calls[state] for state, vec in vecs.items())
        gx = sum(count * calls[state] for state, vec in vecs.items() for block, count in vec.items()
                 if os.path.basename(slots.get(block, ("",))[0]) == "gx_cuda.so")
        if gx:
            errors.append(f"{name}: {gx:,.0f} GX module instructions remain")
        if dropped:
            errors.append(f"{name}: {dropped} calls had dropped/overflow states")
        if not calls:
            errors.append(f"{name}: no usable calls")
        prepared[name] = (pcvs, dropped, vecs, calls, total, gx)
    if errors:
        raise ValueError("invalid drperf collection:\n - " + "\n - ".join(sorted(set(errors))))
    regions = {}
    all_symbols = Counter()
    for name in names:
        pcvs, dropped, vecs, calls, total, gx = prepared[name]
        symbols = Counter()
        for state, vec in vecs.items():
            for block, count in vec.items():
                module, symbol = slots.get(block, ("?", "?"))[:2]
                symbols[(os.path.basename(module), symbol)] += count * calls[state]
        all_symbols.update(symbols)
        points = sorted(vecs)
        varying = [i for i in range(len(pcvs)) if len({v[i] for v in points}) > 1]
        fixed_pcvs = {pcvs[i]: points[0][i] for i in range(len(pcvs)) if i not in varying} if points else {}
        rank_deficient = []
        if points and pcvs:
            _, _, _, dependent = derive.affine_fit(points, [0.0] * len(points))
            rank_deficient = [pcvs[i] for i in sorted(dependent)]
        sufficient = len(points) >= max(derive.MIN_VALUES, len(pcvs) + 2)
        identifiable = sufficient and not rank_deficient and bool(pcvs)
        warnings = []
        if not pcvs:
            warnings.append("no numeric declared PCV; no cost relation can be identified")
        if len(points) == 1:
            warnings.append("one observed state; a constant cost is not a discovered relation")
        elif not sufficient:
            warnings.append("too few distinct states for an affine relation")
        if rank_deficient:
            warnings.append("rank-deficient PCVs: " + ", ".join(rank_deficient))
        model_list = derive.derive(vecs, slots, split=False) if identifiable else []
        model = model_list[0] if model_list else None
        conditional_fit = None
        if not identifiable and fixed_pcvs and varying:
            projected = {tuple(v[i] for i in varying): vecs[v] for v in points}
            enough_projected = (len(projected) == len(points) and
                                len(projected) >= max(derive.MIN_VALUES, len(varying) + 2))
            if enough_projected:
                _, _, _, projected_dependent = derive.affine_fit(
                    sorted(projected), [0.0] * len(projected))
                if not projected_dependent:
                    conditional_models = derive.derive(projected, slots, split=False)
                    if conditional_models:
                        conditional = conditional_models[0]
                        conditional_fit = {
                            "condition": fixed_pcvs,
                            "coefficients": dict(zip((pcvs[i] for i in varying), conditional.a)),
                            "constant": conditional.c,
                            "max_unexplained_fraction": max((
                                conditional.irr.get(v, 0) / sum(projected[v].values())
                                for v in conditional.values if sum(projected[v].values())), default=0.0),
                            "max_reconstruction_error_fraction": max((
                                abs(conditional.total(v) - sum(projected[v].values())) /
                                sum(projected[v].values()) for v in conditional.values
                                if sum(projected[v].values())), default=0.0),
                        }
        max_unexplained = None
        max_reconstruction_error = None
        irregular_symbols = []
        if model:
            max_unexplained = max((model.irr.get(v, 0) / sum(vecs[v].values())
                                   for v in model.values if sum(vecs[v].values())), default=0.0)
            max_reconstruction_error = max((abs(model.total(v) - sum(vecs[v].values())) /
                                            sum(vecs[v].values()) for v in model.values
                                            if sum(vecs[v].values())), default=0.0)
            irregular_symbols = top_functions(Counter({(os.path.basename(mod), sym): value
                                                       for (mod, sym), value in model.by_sym_irr.items()}))
        regions[name] = {
            "calls": sum(calls.values()), "exclusive_instructions": round(total),
            "mean_exclusive_instructions": total / sum(calls.values()) if calls else None,
            "gx_module_instructions": round(gx), "declared_pcvs": list(pcvs),
            "distinct_states": len(points), "state_values": [list(v) for v in points],
            "dropped_calls": dropped, "affine_identifiable": identifiable,
            "rank_deficient_pcvs": rank_deficient,
            "fixed_pcv_observations": fixed_pcvs,
            "conditional_fit": conditional_fit,
            "coefficients": dict(zip(pcvs, model.a)) if model else None,
            "constant": model.c if model else None,
            "max_unexplained_fraction": max_unexplained,
            "max_reconstruction_error_fraction": max_reconstruction_error,
            "top_exclusive_functions": top_functions(symbols),
            "top_irregular_functions_mean_per_state": irregular_symbols,
            "warnings": warnings,
        }
    return {
        "schema": "causal-video-drperf-summary-v1", "input_raw": str(raw),
        "validity": [], "counters": counters, "regions": regions,
        "excluded_setup_regions": sorted(setup_regions),
        "total_marked_exclusive_instructions": sum(r["exclusive_instructions"] for r in regions.values()),
        "top_exclusive_functions": top_functions(all_symbols, 20),
        "limitations": [
            "Exclusive basic-block instructions are summed across marked regions without nested double counting.",
            "A fitted affine relation describes observed states only; it is not evidence of causation or GPU time.",
            "Irregular function ranking is mean instructions per observed state, not total weighted cost.",
        ],
    }


def markdown(report):
    lines = ["# drperf causal-video summary", "",
             f"Valid collection; total marked exclusive instructions: {formatted(report['total_marked_exclusive_instructions'])}.",
             "", "| Region | Calls | Exclusive instructions | Mean/call | PCVs | States | Fit | Max unexplained |",
             "|---|---:|---:|---:|---|---:|---|---:|"]
    for name, row in sorted(report["regions"].items(), key=lambda item: -item[1]["exclusive_instructions"]):
        fraction = row["max_unexplained_fraction"]
        lines.append(f"| {name} | {formatted(row['calls'])} | {formatted(row['exclusive_instructions'])} | "
                     f"{formatted(row['mean_exclusive_instructions'])} | {', '.join(row['declared_pcvs']) or '—'} | "
                     f"{row['distinct_states']} | {'identified' if row['affine_identifiable'] else 'insufficient'} | "
                     f"{fraction:.1%} |" if fraction is not None else
                     f"| {name} | {formatted(row['calls'])} | {formatted(row['exclusive_instructions'])} | "
                     f"{formatted(row['mean_exclusive_instructions'])} | {', '.join(row['declared_pcvs']) or '—'} | "
                     f"{row['distinct_states']} | insufficient | — |")
    lines += ["", "## Relations and diagnostics", ""]
    for name, row in sorted(report["regions"].items(), key=lambda item: -item[1]["exclusive_instructions"]):
        if row["affine_identifiable"]:
            terms = [f"{value:.3g} × {key}" for key, value in row["coefficients"].items()]
            lines.append(f"- **{name}:** " + " + ".join(terms + [f"{row['constant']:.3g}"]) +
                         f" instructions/call; max unexplained {row['max_unexplained_fraction']:.1%}.")
        elif row["conditional_fit"]:
            fit = row["conditional_fit"]
            terms = [f"{value:.3g} × {key}" for key, value in fit["coefficients"].items()]
            condition = ", ".join(f"{key}={value}" for key, value in fit["condition"].items())
            lines.append(f"- **{name}:** conditional on {condition}, " +
                         " + ".join(terms + [f"{fit['constant']:.3g}"]) +
                         f" instructions/call; max unexplained {fit['max_unexplained_fraction']:.1%}. " +
                         "Full declared-PCV model remains unidentifiable.")
        else:
            lines.append(f"- **{name}:** " + "; ".join(row["warnings"]))
    lines += ["", "## Largest exclusive functions", ""]
    for row in report["top_exclusive_functions"][:12]:
        lines.append(f"- `{row['module']}:{row['symbol']}`: {formatted(row['instructions'])}")
    lines += ["", "The relation describes observed PCV states only. It does not measure GPU execution time or identify a critical-path bottleneck.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="managed run directory or drperf/raw directory")
    parser.add_argument("--output-prefix", type=Path, help="output path without .json/.md/.tsv suffix")
    args = parser.parse_args()
    try:
        report = summarize(args.input)
    except (ValueError, OSError, KeyError, IndexError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    prefix = args.output_prefix or (args.input / "drperf-summary" if args.input.is_dir() else args.input)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    prefix.with_suffix(".md").write_text(markdown(report))
    with prefix.with_suffix(".tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(("region", "calls", "exclusive_instructions", "mean_per_call", "pcvs", "states",
                         "affine_identifiable", "constant", "coefficients", "max_unexplained_fraction",
                         "fixed_pcv_observations", "conditional_fit", "warnings"))
        for name, row in sorted(report["regions"].items(), key=lambda item: -item[1]["exclusive_instructions"]):
            writer.writerow((name, row["calls"], row["exclusive_instructions"], row["mean_exclusive_instructions"],
                             ",".join(row["declared_pcvs"]), row["distinct_states"], row["affine_identifiable"],
                             row["constant"], json.dumps(row["coefficients"]), row["max_unexplained_fraction"],
                             json.dumps(row["fixed_pcv_observations"]), json.dumps(row["conditional_fit"]),
                             "; ".join(row["warnings"])))
    print(f"valid drperf summary: {prefix}.json/.md/.tsv")


if __name__ == "__main__":
    main()
