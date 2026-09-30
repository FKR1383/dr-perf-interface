"""Portable, source-linked region models and symbolic nested-work composition.

The exporter reuses drperf's block-level checker. Relationship discovery reports
finite-trace equalities, never causal claims. The UI can explicitly adopt these
as assumptions for replay of the recorded call sequence.
"""
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

import derive
import composition
import markers
import runner
import waits
import event_model
import report_storage

SCHEMA = "drperf.explorer.v1"
SAFE_INTEGER = (1 << 53) - 1
SOURCE_SUFFIXES = {".py", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".rs"}
SKIP_DIRS = {".git", "node_modules", "third_party", "__pycache__", "build", "target", ".venv", "out"}


def write_model(model, destination):
    """Publish a complete JSON report atomically, recomputing its content ID."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    model = portable(report_storage.externalize_waits(model, destination))
    model.pop("id", None)
    model["id"] = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=destination.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(model, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        temporary.replace(destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def load_model(path, wait_evidence=False):
    """View the small report, or explicitly load full evidence for checking."""
    return report_storage.load_model(path, wait_evidence=wait_evidence)


def relation_text(relation):
    terms = []
    for term in relation["terms"]:
        field = term["region"] + ("." + term["state"] if term["state"] is not None else "")
        terms.append(f"{term['coefficientExact']}*{term['kind']}({field})")
    if relation["constant"]:
        terms.append(relation["constantExact"])
    target = relation["target"]
    return (f"{target['region']}.{target['state']} = " + " + ".join(terms)).replace("+ -", "- ")


def cost_lines(model):
    """Render the already-checked portable interfaces; do not fit them twice."""
    # Portable reports encode large int64 state values as decimal strings.
    # Keep them exact when printing bounds instead of passing strings to the
    # numerical coefficient formatter (or converting through a float).
    def boundary(value):
        return f"{int(value):,}" if isinstance(value, str) else derive.fmt(value)

    lines = []
    for region in model["regions"]:
        if not region["regimes"]:
            calls = sum(point["calls"] for point in region["points"])
            mean = sum(point["observed"] * point["calls"] for point in region["points"]) / calls if calls else 0
            lines.append("  %s = %s   (observed mean; no exported fit)" % (region["name"], derive.fmt(mean)))
            continue
        for fit in region["regimes"]:
            terms = ["%s*%s" % (derive.fmt(a), state) for a, state in zip(fit["coefficients"], region["states"]) if a]
            terms.append(derive.fmt(fit["constant"]))
            notes = ["%.1f%% unexplained" % (100 * fit["unexplainedShare"])]
            if fit["dependent"]:
                notes.append("tied PCVs: " + ", ".join(fit["dependent"]))
            if len(region["regimes"]) > 1:
                notes.append(", ".join("%s <= %s <= %s" % (boundary(lo), state, boundary(hi))
                                       for state, (lo, hi) in zip(region["states"], fit["range"])))
            lines.append("  %s = %s   (%s)" % (region["name"], " + ".join(terms), "; ".join(notes)))
            groups = list(zip(region["states"], fit["attribution"]["coefficients"]))
            groups += [("constant", fit["attribution"]["constant"]), ("unexplained", fit["attribution"]["unexplained"])]
            for label, functions in groups:
                if functions:
                    lines.append("      %s: %s" % (label, ", ".join("%s %s [%s]" %
                                 (derive.fmt(row["instructions"]), row["function"], row["module"])
                                 for row in functions[:3])))
        for message in region.get("diagnostics", []):
            lines.append("      note: " + message)
    if "composition" in model:
        lines.extend(composition.lines(model["composition"]))
    lines.extend(waits.lines(model.get("waits")))
    return lines


def node_id(region, state):
    return json.dumps([region, state], ensure_ascii=False, separators=(",", ":"))


def integer(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    return None


def portable(value):
    """Never round an int64 merely to get it into a JavaScript viewer."""
    if isinstance(value, int) and abs(value) > SAFE_INTEGER:
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite measurement in model")
    if isinstance(value, dict):
        return {str(k): portable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(v) for v in value]
    return value


def application_region(name):
    return not name.startswith((runner.CALIB, "_perfmark", "perf.")) and ":" not in name


def normalise_keys(keys):
    """Align identical named schemas; never fit values against the wrong names."""
    schemas = {}
    result = {}
    for key, original in keys.items():
        row = dict(original)
        names = tuple(n for n, _ in row["states"])
        if names and not row.get("overflow"):
            expected = schemas.setdefault(row["region"], names)
            if len(set(names)) != len(names) or set(names) != set(expected):
                row["overflow"] = True
            else:
                values = dict(row["states"])
                row["states"] = [(n, values[n]) for n in expected]
        result[key] = row
    return result


def split_schemas(keys, records):
    """A region name with incompatible PCV schemas denotes multiple interfaces.

    Reordering the same named PCVs is harmless; changing the names is not.
    Stable variant IDs retain the original source name in their metadata.
    """
    schemas = defaultdict(set)
    for row in keys.values():
        if not row.get("overflow") and row.get("count", 0) > 0:
            schemas[row["region"]].add(tuple(sorted(name for name, _value in row["states"])))
    variants, metadata = {}, {}
    for name, choices in schemas.items():
        if len(choices) <= 1:
            metadata[name] = {"originalName": name, "displayName": name}
            continue
        for schema in sorted(choices):
            digest = hashlib.sha256(json.dumps([name, schema]).encode()).hexdigest()[:10]
            variant = name + "@pcv-" + digest
            variants[(name, schema)] = variant
            metadata[variant] = {"originalName": name, "displayName": name + " (" + ", ".join(schema) + ")",
                                 "schemaVariant": True}
    result = {}
    for key, original in keys.items():
        row = dict(original)
        schema = tuple(sorted(name for name, _value in row["states"]))
        row["region"] = variants.get((row["region"], schema), row["region"])
        result[key] = row
    traces = []
    for original in records:
        record = dict(original)
        fields = list(record.get("state", {}))
        count = record.get("nk", 1 if fields else 0)
        schema = tuple(sorted(fields[:count]))
        record["region"] = variants.get((record["region"], schema), record["region"])
        traces.append(record)
    return result, traces, metadata


def source_files(root, explicit=None, limit=5000):
    root = Path(root).resolve()
    if explicit:
        for item in explicit:
            path = (root / item).resolve()
            if path.is_relative_to(root) and path.is_file():
                yield path
        return
    # Skip symlinks: source discovery should stay in the selected source tree.
    import os
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix in SOURCE_SUFFIXES and not path.is_symlink():
                if count >= limit:
                    return
                count += 1
                yield path


def source_locations(root, region_names, explicit=None):
    """Candidate annotation locations, with source hashes for staleness checks."""
    found = defaultdict(list)
    root = Path(root).resolve()
    names = set(region_names)
    for path in source_files(root, explicit):
        if path.stat().st_size > 2_000_000:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        hits = []
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
            for call in ast.walk(tree):
                if not isinstance(call, ast.Call) or not call.args:
                    continue
                func = call.func
                label = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if label not in ("region", "marked", "begin", "perfmark_begin", "perfmark_begin_v"):
                    continue
                arg = call.args[0]
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str) or arg.value not in names:
                    continue
                end = call.end_lineno
                parent = parents.get(call)
                if isinstance(parent, ast.withitem):
                    end = parents[parent].end_lineno
                elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and call in parent.decorator_list:
                    end = parent.end_lineno
                elif label in ("begin", "perfmark_begin", "perfmark_begin_v") and isinstance(parent, ast.Expr):
                    container = parents.get(parent)
                    body = next((value for _field, value in ast.iter_fields(container)
                                 if isinstance(value, list) and parent in value), []) if container else []
                    depth = 1
                    for statement in body[body.index(parent)+1:] if body else []:
                        nested = statement.value if isinstance(statement, ast.Expr) else None
                        if not isinstance(nested, ast.Call) or not nested.args:
                            continue
                        head = nested.func.attr if isinstance(nested.func, ast.Attribute) else getattr(nested.func, "id", "")
                        name = nested.args[0]
                        if not isinstance(name, ast.Constant) or name.value != arg.value:
                            continue
                        if head in ("begin", "perfmark_begin", "perfmark_begin_v"):
                            depth += 1
                        elif head in ("end", "perfmark_end"):
                            depth -= 1
                            if depth == 0:
                                end = nested.end_lineno
                                break
                expressions = {kw.arg: ast.get_source_segment(text, kw.value) or ""
                               for kw in call.keywords if kw.arg}
                if label == "marked" and len(call.args) > 1 and isinstance(call.args[1], ast.Lambda):
                    body = call.args[1].body
                    if isinstance(body, ast.Call) and isinstance(body.func, ast.Name) and body.func.id == "dict":
                        expressions.update({kw.arg: ast.get_source_segment(text, kw.value) or ""
                                            for kw in body.keywords if kw.arg})
                hits.append((arg.value, call.lineno, end, expressions))
        else:
            # Preserve line offsets while excluding comments from marker matching.
            clean = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/',
                           lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]) if m[0].startswith(('/',)) else m[0], text)
            pattern = r'(?:\bperfmark_begin(?:_v)?|\bRegion::new|\bperfmark::region!)\s*\(\s*"((?:[^"\\]|\\.)*)"'
            for match in re.finditer(pattern, clean):
                try:
                    name = json.loads('"' + match[1] + '"')
                except ValueError:
                    continue
                if name not in names:
                    continue
                line = clean.count("\n", 0, match.start()) + 1
                end = line
                # C markers delimit a span; nested same-name markers are ambiguous.
                closes = list(re.finditer(r'\bperfmark_end\s*\(\s*"' + re.escape(match[1]) + r'"', clean[match.end():]))
                if closes:
                    end = clean.count("\n", 0, match.end() + closes[0].start()) + 1
                hits.append((name, line, end, {}))
        for name, line, end, expressions in hits:
            found[name].append({"path": str(path.relative_to(root)), "line": line,
                                "endLine": end, "sha256": hashlib.sha256(raw).hexdigest(),
                                "expressions": expressions})
    return found


def canonical_traces(records, allowed, schemas=None):
    traces = []
    errors = []
    seen = set()
    for r in records:
        if r.get("region") not in allowed:
            continue
        try:
            seq, end = int(r["seq"]), int(r["seq_end"])
            group = str(r.get("run", 0)) + ":" + str(r.get("pid", 0))
            if end <= seq or (group, seq) in seen or (group, end) in seen:
                raise ValueError("invalid or duplicate sequence number")
            seen.update(((group, seq), (group, end)))
            values = {str(k): integer(v) for k, v in r.get("state", {}).items()}
            if schemas is not None:
                declared = schemas.get(r["region"], ())
                if any(values.get(name) is None for name in declared):
                    errors.append("trace call missing declared integer PCV in " + r["region"])
                values = {name: values[name] for name in declared if values.get(name) is not None}
            else:
                values = {k: v for k, v in values.items() if v is not None}
            traces.append({"group": group, "seq": seq, "end": end, "thread": str(r["tid"]),
                           "region": r["region"], "values": values})
        except (KeyError, TypeError, ValueError) as error:
            errors.append(str(error))
    traces.sort(key=lambda r: (r["group"], r["seq"]))
    active = defaultdict(list)
    for event in traces:
        stack = active[(event["group"], event["thread"])]
        while stack and stack[-1] < event["seq"]:
            stack.pop()
        if stack and event["end"] > stack[-1]:
            errors.append("crossing region boundaries on one thread")
        stack.append(event["end"])
    return traces, sorted(set(errors))


def feature_table(traces, max_cells=24_000_000):
    """History is reset per process/run. No cross-run cumulative leakage."""
    states = defaultdict(set)
    for event in traces:
        states[event["region"]].update(event["values"])
    features = []
    for region in sorted(states):
        features.append({"kind": "count", "region": region, "state": None})
        for state in sorted(states[region]):
            # Prefer last-value interpretations when finite observations tie.
            for kind in ("last", "cum", "cumend"):
                features.append({"kind": kind, "region": region, "state": state})
    if len(features) * len(traces) > max_cells:
        return features, [], "relationship discovery skipped: feature-table budget exceeded"
    index = {(f["kind"], f["region"], f["state"]): i for i, f in enumerate(features)}
    rows = []
    for _, group_iter in itertools.groupby(traces, key=lambda e: e["group"]):
        group = list(group_iter)
        ended = sorted(group, key=lambda e: e["end"])
        ending = 0
        values = [0] * len(features)
        for event in group:
            while ending < len(ended) and ended[ending]["end"] < event["seq"]:
                previous = ended[ending]
                for state, value in previous["values"].items():
                    values[index[("cumend", previous["region"], state)]] += value
                ending += 1
            rows.append(values[:])
            region = event["region"]
            values[index[("count", region, None)]] += 1
            for state, value in event["values"].items():
                values[index[("last", region, state)]] = value
                values[index[("cum", region, state)]] += value
    return features, rows, None


def relation_discovery(traces, max_candidates=200_000, max_per_target=4, max_features=24):
    features, table, warning = feature_table(traces)
    meta = {"candidateBudget": max_candidates, "candidatesTested": 0, "truncated": False,
            "scope": "exact finite-trace equalities; discovery is bounded, not exhaustive",
            "warnings": [warning] if warning else []}
    if not table:
        meta["truncated"] = bool(warning)
        return [], meta
    targets = defaultdict(list)
    for i, event in enumerate(traces):
        for state, value in event["values"].items():
            targets[(event["region"], state)].append((i, value))
    relations = []
    eligible = [(target, points) for target, points in sorted(targets.items())
                if len(points) >= 5 and len({y for _, y in points}) >= 3]
    for target_index, ((region, state), points) in enumerate(eligible):
        # Divide remaining work among remaining targets; an early difficult
        # region must not starve all later regions of even singleton checks.
        remaining = max_candidates - meta["candidatesTested"]
        target_limit = meta["candidatesTested"] + remaining // (len(eligible) - target_index)
        ys = [y for _, y in points]
        columns, aliases, by_values = [], {}, {}
        for j, feature in enumerate(features):
            col = tuple(table[i][j] for i, _ in points)
            if len(set(col)) < 2:
                continue
            if col in by_values:
                aliases.setdefault(by_values[col], []).append(j)
            else:
                by_values[col] = j
                columns.append((j, col))
        found = []

        def accept(js, coefficients, offset):
            # History of this same state alone rarely provides a useful cross-region edge.
            if all(features[j]["region"] == region for j in js):
                return
            signature = (tuple(js), tuple(coefficients), offset)
            if signature in found:
                return
            found.append(signature)
            terms = [{**features[j], "coefficient": float(c),
                      "coefficientExact": str(c), "aliases": [features[a] for a in aliases.get(j, [])]}
                     for j, c in zip(js, coefficients)]
            equation = {"target": {"region": region, "state": state}, "terms": terms,
                        "constant": float(offset), "constantExact": str(offset),
                        "evidence": {"kind": "observed", "exact": True, "calls": len(points),
                                     "groups": len({traces[i]["group"] for i, _ in points}),
                                     "distinctTargetValues": len(set(ys))},
                        "semantics": "history before the target call in marker sequence order"}
            payload = json.dumps(equation, sort_keys=True)
            equation["id"] = hashlib.sha256(payload.encode()).hexdigest()[:16]
            relations.append(equation)

        for j, col in columns:
            if meta["candidatesTested"] >= target_limit:
                meta["truncated"] = True
                break
            second = next(i for i, x in enumerate(col) if x != col[0])
            c = Fraction(ys[second] - ys[0], col[second] - col[0])
            d = ys[0] - c * col[0]
            meta["candidatesTested"] += 1
            if c and c.denominator <= 1024 and all(c*x+d == y for x, y in zip(col, ys)):
                accept([j], [c], d)
            if len(found) >= max_per_target:
                break
        if found:
            continue
        # Try conservation-style relationships, e.g. queue = cum(push)-cum(pop).
        # Feature and candidate budgets prevent combinatorial stalls on large models.
        candidates = sorted(columns, key=lambda p: (features[p[0]]["kind"] == "count", p[0]))[:max_features]
        stop = False
        for k in (2, 3):
            if stop:
                break
            for combo in itertools.combinations(candidates, k):
                if stop:
                    break
                js = [j for j, _ in combo]
                for coefficients in itertools.product((1, -1, 2, -2), repeat=k):
                    if meta["candidatesTested"] >= target_limit:
                        meta["truncated"] = True
                        stop = True
                        break
                    meta["candidatesTested"] += 1
                    d = ys[0] - sum(c*col[0] for c, (_, col) in zip(coefficients, combo))
                    if all(sum(c*col[i] for c, (_, col) in zip(coefficients, combo))+d == ys[i]
                           for i in range(1, len(ys))):
                        accept(js, [Fraction(c) for c in coefficients], Fraction(d))
                        if len(found) >= max_per_target:
                            stop = True
                            break
    return relations, meta


def attributed(mapping, limit=8):
    return [{"module": mod, "function": symbol, "instructions": value}
            for (mod, symbol), value in sorted(mapping.items(), key=lambda x: -abs(x[1]))[:limit]]


def load_raw_runs(raw):
    """Ignore explorer/client summaries in the same directory as raw runs."""
    runs = []
    for path in sorted(Path(raw).glob("*.json")):
        if not Path(str(path) + ".blocks").is_file():
            continue
        data = json.loads(path.read_text())
        if isinstance(data, dict) and isinstance(data.get("drperf"), dict) and isinstance(data.get("regions"), list):
            runs.append({"data": data, "file": path.name})
    return {"label": str(raw), "path": str(raw), "runs": runs}


def load_local_traces(runs):
    """Read the sidecars belonging to this export, never a stale absolute path."""
    records, errors = [], []
    for index, run in enumerate(runs["runs"]):
        metadata = run["data"]["drperf"]
        candidates = [Path(runs["path"]) / (run["file"] + ".trace")]
        if metadata.get("trace_file"):
            candidates.append(Path(runs["path"]) / Path(metadata["trace_file"]).name)
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            errors.append("missing trace sidecar for " + run["file"])
            continue
        count = 0
        with path.open() as stream:
            for line in stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                record["run"], record["pid"] = index, metadata.get("pid", 0)
                records.append(record)
                count += 1
        if metadata.get("trace_records") is not None and count != metadata["trace_records"]:
            errors.append("trace record count disagrees with report for " + run["file"])
    return records, errors


def nesting_statistics(records):
    """All region nesting summaries in O(markers * active nesting depth).

    Preserve the existing reader's exclusion of recursive same-name markers and
    instrumentation regions. No cross-thread or cross-process nesting is inferred.
    """
    groups, parents, children = defaultdict(list), Counter(), defaultdict(Counter)
    for record in records:
        groups[(record.get("run", 0), record.get("pid", 0), record["tid"])].append(record)
    for group in groups.values():
        active = []
        for record in sorted(group, key=lambda r: r["seq"]):
            name = record["region"]
            active = [parent for parent in active if parent["seq_end"] >= record["seq"]]
            if ":" not in name and name != "_perfmark_capture":
                for parent in active:
                    if parent["region"] != name and parent["seq"] < record["seq"] and record["seq_end"] <= parent["seq_end"]:
                        children[parent["region"]][name] += 1
            parents[name] += 1
            active.append(record)
    return {name: {child: count / parents[name] for child, count in children[name].items()} for name in parents}


def build_model(raw, source_root=None, source_paths=None, discover=True, max_trace=50_000,
                relation_budget=200_000):
    raw = Path(raw).resolve()
    if not raw.is_dir():
        raise ValueError("RAW must be a directory containing run JSON and .blocks/.slots files")
    runs = load_raw_runs(raw)
    if not runs["runs"]:
        raise ValueError("no drperf run reports found")
    keys, slots = runner.blocks_of_set(runs)
    if not keys:
        raise ValueError("no block counts found; run drperf with block output enabled")
    records, trace_errors = load_local_traces(runs)
    keys, records, interface_metadata = split_schemas(keys, records)
    keys = normalise_keys(keys)
    slots = runner.demangle_slots(slots)
    names = sorted({k["region"] for k in keys.values() if application_region(k["region"])})
    schemas = {name: derive.per_state(keys, name)[1] for name in names}
    traces, canonical_errors = canonical_traces(records, set(names), schemas)
    trace_errors += canonical_errors
    nested_by_region = nesting_statistics(records)
    complete = len(traces) <= max_trace
    trace_count = len(traces)
    if not complete:
        traces = []  # A prefix would create misleading complete-looking scenarios.
    raw_keys = keys
    keys, marker_accounting = markers.adjust(keys, slots, records, trace_errors + runner.validity(runs))
    source_names = {interface_metadata.get(name, {}).get("originalName", name) for name in names}
    locations = source_locations(source_root, source_names, source_paths) if source_root else {}
    regions = []
    for name in names:
        own, states, dropped = derive.per_state(keys, name)
        vecs, calls = derive.per_trigger(own)
        nested = nested_by_region.get(name, {})
        calibration = 0
        fitted = derive.derive(vecs, slots)
        regimes = []
        for fit in fitted:
            regimes.append({"coefficients": list(fit.a), "constant": fit.c,
                            "dependent": [states[i] for i in sorted(fit.dependent)],
                            "points": [{"state": list(v), "calls": calls[v],
                                        "explained": fit.formula(v), "unexplained": fit.irr.get(v, 0),
                                        "waiting": fit.wait.get(v, 0)} for v in fit.values],
                            "range": [[min(v[j] for v in fit.values), max(v[j] for v in fit.values)]
                                      for j in range(len(states))],
                            "unexplainedShare": fit.irr_share(),
                            "blocks": {"affine": fit.n_affine, "constant": fit.n_const,
                                       "unexplained": fit.n_irr},
                            "attribution": {"coefficients": [attributed(m) for m in fit.by_sym_a],
                                            "constant": attributed(fit.by_sym_c),
                                            "unexplained": attributed(fit.by_sym_irr)},
                            "markerCalibration": calibration})
        points = []
        raw_own, _raw_states, _raw_dropped = derive.per_state(raw_keys, name)
        raw_vecs, _raw_calls = derive.per_trigger(raw_own)
        for v, vec in sorted(vecs.items()):
            recorded = sum(c for b, c in raw_vecs[v].items() if not derive.is_runtime(slots.get(b, ("?", "?", None))[:2]))
            observed = sum(c for b, c in vec.items() if not derive.is_runtime(slots.get(b, ("?", "?", None))[:2]))
            points.append({"state": list(v), "calls": calls[v], "recorded": recorded,
                           "observed": observed})
        marker_info = markers.metadata(name, states, marker_accounting)
        raw_regimes = []
        for fit in derive.derive(raw_vecs, slots):
            raw_regimes.append({"coefficients": list(fit.a), "constant": fit.c,
                               "dependent": [states[i] for i in sorted(fit.dependent)],
                               "points": [{"state": list(v), "calls": calls[v], "explained": fit.formula(v),
                                           "unexplained": fit.irr.get(v, 0), "waiting": fit.wait.get(v, 0)} for v in fit.values],
                               "range": [[min(v[j] for v in fit.values), max(v[j] for v in fit.values)] for j in range(len(states))],
                               "unexplainedShare": fit.irr_share(),
                               "blocks": {"affine": fit.n_affine, "constant": fit.n_const, "unexplained": fit.n_irr},
                               "attribution": {"coefficients": [attributed(m) for m in fit.by_sym_a],
                                               "constant": attributed(fit.by_sym_c), "unexplained": attributed(fit.by_sym_irr)},
                               "markerCalibration": 0})
        diagnostics = []
        if any(point["observed"] < 0 for point in points):
            diagnostics.append("Observed costs are negative. Inspect recorded counts; predictions are unavailable at those states.")
        if any(point["explained"] < 0 for fit in regimes for point in fit["points"]):
            diagnostics.append("The explained formula is negative at some recorded states. These states cannot support scenario cost predictions.")
        info = interface_metadata.get(name, {"originalName": name, "displayName": name})
        if info.get("schemaVariant"):
            diagnostics.append("This region name was used with different PCV schemas. Each schema is displayed and checked as a separate interface.")
        regions.append({"id": name, "name": info["displayName"], "originalName": info["originalName"], "states": list(states),
                        "markerCalibration": calibration, "diagnostics": diagnostics,
                        "markerAdjustment": marker_info, "recordedRegimes": raw_regimes,
                        "calls": sum(calls.values()), "droppedCalls": dropped,
                        "status": "modelled" if regimes else "no-observations",
                        "regimes": regimes, "points": points,
                        "nested": nested, "sources": locations.get(info["originalName"], [])})
    if discover and complete and not trace_errors:
        relations, discovery = relation_discovery(traces, max_candidates=relation_budget)
    else:
        relations, discovery = [], {"truncated": False, "warnings": [],
                                    "scope": "discovery disabled or complete trace unavailable"}
    invalid = runner.validity(runs)
    composed = composition.build(regions, traces, invalid + trace_errors +
                                 ([] if complete else ["trace exceeds export limit"]))
    model = {"schema": SCHEMA, "title": raw.name, "measurement": {
                 "unit": "CPU instructions per call", "scope": "exclusive region work",
                 "markerAdjustment": "marker modules excluded exactly; no wrapper calibration subtraction",
                 "composition": "symbolic direct-child work in composition; no latency or parallelism model",
                 "tolerance": {"absolute": derive.ABS_TOL, "relative": derive.REL_TOL}},
             "provenance": {"rawDirectory": str(raw), "sourceRoot": str(Path(source_root).resolve()) if source_root else None,
                            "runs": [{"file": r["file"], "measurement": r["data"].get("drperf", {})} for r in runs["runs"]]},
             "validity": {"errors": invalid, "traceErrors": trace_errors},
             "regions": regions, "relations": relations, "discovery": discovery,
             "composition": composed,
             "trace": {"complete": complete and not trace_errors, "recordCount": trace_count,
                       "limit": max_trace, "events": traces},
             "scenarioContract": {"fixed": ["recorded call count", "marker sequence order", "nesting"],
                                  "unknown": ["causality of observed relationships", "unexplained cost at changed states",
                                              "new branches or calls", "CPU/GPU latency and overlap"],
                                  "requiresExplicitAssumptions": True}}
    synchronization = waits.build(runs, regions, traces, invalid + trace_errors +
                                  ([] if complete else ["Region trace exceeds export limit."]))
    if synchronization is not None:
        model["waits"] = synchronization
        declared_events = event_model.check(model)
        if declared_events is not None:
            model["eventModel"] = declared_events
    # Keep the checked region graph portable: viewers need no Python/Graphviz
    # process, raw sidecars, or fresh application execution to display it.
    import execution
    model["executionGraph"] = execution.build(model)
    model = portable(model)
    model["id"] = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()
    return model
