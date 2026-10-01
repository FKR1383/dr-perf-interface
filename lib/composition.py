"""Hierarchical cost interfaces over observed, same-thread marker nesting.

Child functions remain opaque, including their unexplained cost. Multiplicity
and argument substitutions are checked separately from instruction counts, in
exact rational arithmetic. No child block is refitted against parent PCVs.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import re

import derive


def _integer(value):
    if isinstance(value, bool) or not (isinstance(value, int) or
                                     isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value)):
        raise ValueError("composition requires exact integer states and counters")
    return int(value)


def affine(rows, values, names):
    """An exact observed affine relation, or None; never a least-squares guess.

    Any nonempty set of inputs can support an observed relation, including
    exactly determined and underdetermined systems. Dependent columns get zero
    coefficients and are disclosed. All relations describe observations only.
    """
    if len(rows) != len(values) or any(len(row) != len(names) for row in rows):
        raise ValueError("affine relation has inconsistent dimensions")
    if not rows:
        return None
    if len(set(values)) == 1:
        return {"coefficients": ["0"] * len(names), "constant": str(values[0]),
                "kind": "observed-constant", "dependent": [], "samples": len(rows)}
    basis = {}
    for row, value in zip(rows, values):
        vector = [Fraction(1)] + [Fraction(x) for x in row] + [Fraction(value)]
        for pivot, old in sorted(basis.items()):
            factor = vector[pivot]
            if factor:
                vector = [x - factor * y for x, y in zip(vector, old)]
        pivot = next((j for j, x in enumerate(vector[:-1]) if x), None)
        if pivot is None:
            if vector[-1]:
                return None
            continue
        scale = vector[pivot]
        basis[pivot] = [x / scale for x in vector]
    solution = [Fraction(0)] * (len(names) + 1)
    for pivot, row in sorted(basis.items(), reverse=True):
        solution[pivot] = row[-1] - sum(row[j] * solution[j]
                                       for j in range(pivot + 1, len(solution)))
    return {"coefficients": [str(x) for x in solution[1:]],
            "constant": str(solution[0]), "kind": "observed-affine",
            "dependent": [name for j, name in enumerate(names, 1) if j not in basis],
            "samples": len(rows)}


def affine_text(relation, names):
    terms = []
    for coefficient, name in zip(relation["coefficients"], names):
        a = Fraction(coefficient)
        if a:
            terms.append(name if a == 1 else f"{a}*{name}")
    c = Fraction(relation["constant"])
    if c or not terms:
        terms.append(str(c))
    return " + ".join(terms).replace("+ -", "- ")


def own_interface(name, names, vecs, calls, fits, slots):
    """Small recorded-count interface for the terminal path (no calibration)."""
    return {"id": name, "states": list(names), "calls": sum(calls.values()),
            "droppedCalls": 0, "markerCalibration": 0,
            "points": [{"state": list(v), "calls": calls[v],
                        "recorded": sum(c for b, c in vec.items()
                                        if not derive.is_runtime(slots.get(b, ("?", "?"))))}
                       for v, vec in sorted(vecs.items())],
            "regimes": [{"coefficients": list(f.a), "constant": f.c,
                         "points": [{"state": list(v), "unexplained": f.irr.get(v, 0)}
                                    for v in f.values]}
                        for f in fits]}


def _forest(regions, traces):
    """Validate full trace/counter coverage and build only direct-child edges."""
    nodes, active, seen, counts = [], defaultdict(list), set(), Counter()
    for event in sorted(traces, key=lambda e: (e["group"], _integer(e["seq"]))):
        name = event["region"]
        if name not in regions:
            raise ValueError("trace region has no cost interface: " + name)
        start, end = _integer(event["seq"]), _integer(event["end"])
        if end <= start or (event["group"], start) in seen or (event["group"], end) in seen:
            raise ValueError("invalid or duplicate trace boundary")
        seen.update(((event["group"], start), (event["group"], end)))
        names = regions[name]["states"]
        if len(names) != len(set(names)):
            raise ValueError("duplicate PCV name in interface: " + name)
        if set(event["values"]) != set(names):
            raise ValueError("trace PCVs do not match interface: " + name)
        state = tuple(_integer(event["values"][n]) for n in names)
        node = {"region": name, "state": state, "end": end, "children": []}
        stack = active[(event["group"], event["thread"])]
        while stack and stack[-1]["end"] < start:
            stack.pop()
        if stack:
            if end >= stack[-1]["end"]:
                raise ValueError("crossing region boundaries")
            stack[-1]["children"].append(node)
        nodes.append(node)
        stack.append(node)
        counts[(name, state)] += 1
    expected = Counter()
    for name, region in regions.items():
        if region.get("droppedCalls"):
            raise ValueError("state budget omitted calls in " + name)
        for point in region["points"]:
            state = tuple(_integer(x) for x in point["state"])
            count = _integer(point["calls"])
            if len(state) != len(region["states"]) or count <= 0:
                raise ValueError("invalid per-state counter in " + name)
            expected[(name, state)] += count
        if sum(_integer(p["calls"]) for p in region["points"]) != _integer(region["calls"]):
            raise ValueError("region call count does not match per-state counters: " + name)
    if counts != expected:
        raise ValueError("trace calls do not match retained per-state counters")
    return nodes


def _edge(parent, child, calls, regions):
    names = regions[parent]["states"]
    child_names = regions[child]["states"]
    index = "j"
    while index in names:
        index = "call_" + index
    rows = [call["state"] for call in calls]
    children = [[node for node in call["children"] if node["region"] == child] for call in calls]
    multiplicity = affine(rows, [len(nodes) for nodes in children], names)
    arguments = {}
    for j, name in enumerate(child_names):
        argument_rows, values = [], []
        for call, nodes in zip(calls, children):
            for node in nodes:
                argument_rows.append(call["state"])
                values.append(node["state"][j])
        relation = affine(argument_rows, values, names)
        if relation is None:
            arguments = None
            break
        arguments[name] = relation
    sequence_arguments = None
    if arguments is None:
        sequence_arguments = {}
        for k, name in enumerate(child_names):
            indexed_rows, values = [], []
            for call, nodes in zip(calls, children):
                for j, node in enumerate(nodes):
                    indexed_rows.append(call["state"] + (j,))
                    values.append(node["state"][k])
            relation = affine(indexed_rows, values, names + [index])
            if relation is None:
                sequence_arguments = None
                break
            sequence_arguments[name] = relation
    return {"child": child, "multiplicity": multiplicity, "arguments": arguments,
            "argumentStates": list(child_names),
            "sequenceArguments": sequence_arguments,
            "indexVariable": index,
            "form": "product" if multiplicity is not None else "unresolved",
            "parentCalls": len(calls), "childCalls": sum(map(len, children)),
            "includesZeroCallParents": any(not nodes for nodes in children)}


def build(region_list, traces, errors=()):
    """Compose frozen own interfaces. F includes unexplained work at every level.

    Numerical inclusive totals are deliberately not fabricated: child block
    counters aggregate by state across callers. Raw traces have per-invocation
    thread-local totals, but not the all-thread, runtime-filtered block breakdown.
    """
    report = {"status": "unavailable", "scope": "same-thread direct-child instruction work",
              "basis": "marker-adjusted own interfaces; runtime waiting excluded; wrapper calibration is an estimate",
              "contract": "Observed calls only. F includes U. U includes descendant unexplained work. "
                          "N*F denotes N applications of an atomic child interface, not N times a global measured mean. "
                          "Argument mappings are metadata, not prerequisites for child multipliers. "
                          "Own cost fits and U tables are per-state means across callers. "
                          "No prediction of per-invocation inclusive counts or latency.",
              "regions": [], "errors": list(errors)}
    if errors:
        return report
    try:
        regions = {r["id"]: r for r in region_list}
        if len(regions) != len(region_list):
            raise ValueError("duplicate region interface")
        if any(len(r["states"]) != len(set(r["states"])) for r in region_list):
            raise ValueError("duplicate PCV name in interface")
        nodes = _forest(regions, traces)
    except (ValueError, KeyError, TypeError) as error:
        report["errors"].append(str(error))
        return report
    calls_by_region = defaultdict(list)
    for node in nodes:
        calls_by_region[node["region"]].append(node)
    edges = {}
    for name, calls in calls_by_region.items():
        children = sorted({child["region"] for call in calls for child in call["children"]})
        edges[name] = [_edge(name, child, calls, regions) for child in children]
    # Iterative postorder; recursive interfaces stay as recurrences, never unrolled.
    order, visiting, done, recursive = [], set(), set(), set()
    for name in sorted(regions):
        stack = [(name, False)]
        while stack:
            current, finish = stack.pop()
            if finish:
                visiting.discard(current)
                if current not in done:
                    done.add(current)
                    order.append(current)
                continue
            if current in visiting:
                recursive.add(current)
                continue
            if current in done:
                continue
            visiting.add(current)
            stack.append((current, True))
            stack.extend((edge["child"], False) for edge in reversed(edges.get(current, [])))
    # Mark every member of a mutually recursive component, not only the DFS
    # back-edge endpoint. Iterative Kosaraju also works for very deep graphs.
    incoming = defaultdict(list)
    for parent, children in edges.items():
        for edge in children:
            incoming[edge["child"]].append(parent)
    assigned = set()
    for name in reversed(order):
        if name in assigned:
            continue
        component, pending = set(), [name]
        while pending:
            current = pending.pop()
            if current in assigned:
                continue
            assigned.add(current)
            component.add(current)
            pending.extend(incoming[current])
        if len(component) > 1:
            recursive.update(component)
    for name in order:
        region = regions[name]
        own = []
        unexplained = {}
        for fit in region["regimes"]:
            own.append({"coefficients": fit["coefficients"],
                        "constant": fit["constant"],
                        "states": [p["state"] for p in fit["points"]]})
            unexplained.update((tuple(int(x) for x in p["state"]), p["unexplained"])
                               for p in fit["points"])
        if not own:
            unexplained = {tuple(int(x) for x in p["state"]): p.get("observed", p["recorded"]) for p in region["points"]}
        observations = defaultdict(lambda: {"calls": 0, "children": Counter(), "counts": defaultdict(list)})
        for call in calls_by_region[name]:
            row = observations[call["state"]]
            row["calls"] += 1
            row["children"].update((child["region"], child["state"]) for child in call["children"])
            counts = Counter(child["region"] for child in call["children"])
            for edge in edges.get(name, []):
                row["counts"][edge["child"]].append(counts[edge["child"]])
        report["regions"].append({"id": name, "states": region["states"],
            "own": own, "ownUnexplained": any(unexplained.values()),
            "children": edges.get(name, []), "recursive": name in recursive,
            "observed": [{"state": list(state), "calls": row["calls"],
                          "ownUnexplained": unexplained.get(state),
                          "childCallRanges": {child: [min(counts), max(counts)]
                                              for child, counts in row["counts"].items()},
                          "children": [{"region": child, "state": list(values), "calls": count}
                                       for (child, values), count in sorted(row["children"].items())]}
                         for state, row in sorted(observations.items())]})
    report["status"] = "observed"
    return report


def _reference(prefix, name, args):
    return f"{prefix}[{name}]({', '.join(args)})"


def _state_text(names, state):
    # Portable JSON keeps int64 PCVs as decimal strings above JS's safe range.
    return derive.fmt_state(names, tuple(int(x) for x in state))


def edge_text(edge, names, prefix="F"):
    """Keep the child interface atomic; argument mappings are metadata only."""
    reference = f"{prefix}[{edge['child']}]"
    if edge["multiplicity"] is None:
        # The full child contribution, not only the child's own irregular part,
        # is unresolved when no allowed parent multiplier explains call count.
        return f"unexplained(F[{edge['child']}])"
    count = affine_text(edge["multiplicity"], names)
    return reference if count == "1" else f"({count})*{reference}"


def lines(report):
    if report["status"] != "observed":
        return ["composition unavailable: " + "; ".join(report["errors"])]
    if not any(r["children"] for r in report["regions"]):
        return []
    out = ["", "composed interfaces (marker-adjusted instructions)",
           "  F includes child unexplained work; U names unexplained work recursively.",
           "  N*F means N child-interface applications, not N times a global measured mean.",
           "  Own fits retain block tolerances; multipliers are exact on observed calls only. Argument maps are separate metadata."]
    for region in report["regions"]:
        name, names = region["id"], region["states"]
        child_terms = [edge_text(edge, names) for edge in region["children"]]
        own_u = _reference("U_own", name, names) if region["ownUnexplained"] else None
        fits = region["own"] or [{"coefficients": [], "constant": 0}]
        for i, fit in enumerate(fits):
            terms = [f"{derive.fmt(a)}*{state}" for a, state in zip(fit["coefficients"], names) if abs(a) > 1e-10]
            if abs(fit["constant"]) > 1e-10 or not terms:
                terms.append(derive.fmt(fit["constant"]))
            terms += ([own_u] if own_u else []) + child_terms
            label = f" [observed regime {i+1}]" if len(fits) > 1 else ""
            out.append("  " + _reference("F", name, names) + " = " + " + ".join(terms).replace("+ -", "- ") + label)
        u_terms = ([own_u] if own_u else []) + [edge_text(edge, names, "U") for edge in region["children"]]
        out.append("    " + _reference("U", name, names) + " = " + (" + ".join(u_terms) or "0"))
        if not region["own"]:
            out.append("    own cost has no exported fit; retained entirely in U_own")
        if region["recursive"]:
            out.append("    recursive reference: a recurrence over observed calls, not a solved bound")
        if own_u:
            observations = region["observed"]
            shown = observations[:12]
            out.append("    U_own per observed state: " + "; ".join(
                _state_text(names, row["state"]) + ": " +
                derive.fmt(int(row["ownUnexplained"]) if isinstance(row["ownUnexplained"], str)
                           else row["ownUnexplained"])
                for row in shown))
            if len(shown) < len(observations):
                out.append(f"    ... {len(observations)-len(shown)} more states in the JSON composition report")
        for edge in region["children"]:
            if edge["multiplicity"] is None:
                out.append("    " + edge["child"] + ": no affine call multiplier fits; full child contribution remains unexplained")
            relations = ([edge["multiplicity"]] + list((edge["arguments"] or {}).values())
                         + list((edge.get("sequenceArguments") or {}).values()))
            for relation in relations:
                if relation and relation["dependent"]:
                    out.append("    tied parent PCVs in call relation: " + ", ".join(relation["dependent"]))
            different = next((row for row in region["observed"]
                              if row["childCallRanges"][edge["child"]][0] !=
                              row["childCallRanges"][edge["child"]][1]), None)
            if different:
                lo, hi = different["childCallRanges"][edge["child"]]
                out.append(f"    {edge['child']}: identical parent state " +
                           _state_text(names, different["state"]) + f" had {lo}..{hi} child calls")
    return out


def check(reference, region_list, traces, errors=()):
    """Check frozen call relations on another execution; do not refit any rule.

    This validates structure/arguments only, not instruction predictions.
    Unknown argument mappings do not block an affine child multiplier.
    An unmodelled call count remains unresolved even when argument checks hold.
    New edges are reported, including edges from a formerly childless region.
    """
    result = {"status": "unavailable", "errors": list(errors), "edges": [], "newEdges": []}
    if reference.get("status") != "observed":
        result["errors"].append("reference composition unavailable")
    if result["errors"]:
        return result
    regions = {r["id"]: r for r in region_list}
    if len(regions) != len(region_list):
        result["errors"].append("duplicate region interface")
        return result
    try:
        nodes = _forest(regions, traces)
    except (ValueError, KeyError, TypeError) as error:
        result["errors"].append(str(error))
        return result
    calls = defaultdict(list)
    actual_edges = set()
    for node in nodes:
        calls[node["region"]].append(node)
        actual_edges.update((node["region"], child["region"]) for child in node["children"])
    reference_edges = set()
    reference_schemas = {r["id"]: r["states"] for r in reference["regions"]}
    def evaluate(relation, state):
        return sum((Fraction(a)*x for a, x in zip(relation["coefficients"], state)),
                   Fraction(relation["constant"]))
    for region in reference["regions"]:
        parent, names = region["id"], region["states"]
        for edge in region["children"]:
            child = edge["child"]
            reference_edges.add((parent, child))
            row = {"parent": parent, "child": child, "checks": 0, "failures": 0,
                   "counterexamples": [], "unresolved": edge["multiplicity"] is None,
                   "argumentsUnresolved": edge.get("arguments") is None and edge.get("sequenceArguments") is None}
            result["edges"].append(row)
            if parent not in regions or not calls[parent]:
                row["status"] = "not-exercised"
                continue
            if set(names) != set(regions[parent]["states"]) or (child in regions and
                    set(edge.get("argumentStates", reference_schemas[child])) != set(regions[child]["states"])):
                row["status"] = "schema-mismatch"
                continue
            def test(kind, relation, state, actual):
                expected = evaluate(relation, state)
                row["checks"] += 1
                if expected != actual:
                    row["failures"] += 1
                    if len(row["counterexamples"]) < 3:
                        row["counterexamples"].append({"kind": kind, "parentState": list(state[:len(names)]),
                                                       "expected": str(expected), "actual": actual})
            for call in calls[parent]:
                state_by_name = dict(zip(regions[parent]["states"], call["state"]))
                state = tuple(state_by_name[n] for n in names)
                children = [node for node in call["children"] if node["region"] == child]
                if edge["multiplicity"] is not None:
                    test("multiplicity", edge["multiplicity"], state, len(children))
                for j, node in enumerate(children):
                    actual = dict(zip(regions[child]["states"], node["state"]))
                    arguments = edge["arguments"] or edge.get("sequenceArguments")
                    if arguments is not None:
                        inputs = state if edge["arguments"] is not None else state + (j,)
                        for name, relation in arguments.items():
                            test("argument:" + name, relation, inputs, actual[name])
            row["status"] = "fails" if row["failures"] else "holds" if row["checks"] else "unresolved"
    result["newEdges"] = [{"parent": p, "child": c} for p, c in sorted(actual_edges - reference_edges)]
    result["status"] = "checked"
    return result
