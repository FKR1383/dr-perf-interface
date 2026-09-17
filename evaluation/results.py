"""Validation and presentation of the two small evaluation contracts."""
import json
import math
from pathlib import Path

MAX_ATTEMPTS = 10


class EvaluationError(ValueError):
    pass


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise EvaluationError(f"cannot read valid JSON from {path}: {exc}") from exc


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def variables(value):
    if not isinstance(value, list) or any(
        not isinstance(v, str) or not v.strip() or v != v.strip() for v in value
    ):
        raise EvaluationError("variables must be an array of nonempty source expressions")
    return sorted(set(value))


def validate_schema(value, schema, where="result"):
    """Only the JSON Schema keywords used in our two checked-in contracts."""
    types = schema["type"]
    types = types if isinstance(types, list) else [types]
    matches = {"object": type(value) is dict, "array": type(value) is list,
               "string": type(value) is str, "integer": type(value) is int,
               "number": type(value) in (int, float), "null": value is None}
    if not any(matches[t] for t in types):
        raise EvaluationError(f"{where}: expected {' or '.join(types)}")
    if isinstance(value, dict):
        props = schema["properties"]
        if set(value) != set(schema["required"]):
            raise EvaluationError(f"{where}: missing or unexpected fields")
        for key, item in value.items():
            validate_schema(item, props[key], f"{where}.{key}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise EvaluationError(f"{where}: at least one measured attempt is required")
        for index, item in enumerate(value):
            validate_schema(item, schema["items"], f"{where}[{index}]")
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or (
            "enum" in schema and value not in schema["enum"]
        ):
            raise EvaluationError(f"{where}: invalid value")
    elif type(value) in (int, float):
        if not math.isfinite(value) or not (
            schema.get("minimum", -math.inf) <= value <= schema.get("maximum", math.inf)
        ):
            raise EvaluationError(f"{where}: number is outside the allowed range")


def validate_result(value, competitor, max_attempts=MAX_ATTEMPTS):
    schema = read_json(Path(__file__).parent / "schemas" / f"{competitor}.json")
    validate_schema(value, schema)
    if competitor == "agent_only":
        value["variables"] = variables(value["variables"])
        return value
    if len(value["attempts"]) > min(max_attempts, MAX_ATTEMPTS):
        raise EvaluationError("experiment limit exceeded")
    for index, attempt in enumerate(value["attempts"], 1):
        attempt["variables"] = variables(attempt["variables"])
        if attempt["attempt"] != index or len(attempt["variables"]) > 4:
            raise EvaluationError("attempts must be consecutive and declare at most four states")
        if attempt["status"] == "ok":
            if not attempt["formula"] or attempt["irregularity"] is None:
                raise EvaluationError("successful measurement requires a formula and irregularity")
        elif attempt["formula"] is not None or attempt["irregularity"] is not None:
            raise EvaluationError("failed measurement must have null formula and irregularity")
    value["selected_variables"] = variables(value["selected_variables"])
    if not any(a["variables"] == value["selected_variables"] and
               a["formula"] == value["final_formula"] and
               a["irregularity"] == value["final_irregularity"] for a in value["attempts"]):
        raise EvaluationError("final selection must match a recorded attempt")
    return value


def best_attempt(attempts):
    """Rank valid measurements; failures never beat a measured model."""
    return min((a for a in attempts if a["status"] == "ok"),
               key=lambda a: (a["irregularity"], len(a["variables"]), a["attempt"]),
               default=None)


def comparison(predicted, truth):
    missing, extra = set(truth) - set(predicted), set(predicted) - set(truth)
    return {"exact_match": not missing and not extra,
            "missing": sorted(missing), "extra": sorted(extra)}


def summary(result):
    def names(items):
        return "{" + ", ".join(items) + "}"

    def percent(value):
        return "n/a" if value is None else f"{100 * value:.4g}%"

    dr = result["agent_drperf"]
    lines = ["=== Agent Only ===", f"variables: {names(result['agent_only']['variables'])}",
             "", "=== Agent + Dr. Perf ==="]
    for a in dr["attempts"]:
        lines += ["", f"attempt {a['attempt']}", f"  variables:    {names(a['variables'])}",
                  f"  formula:      {a['formula'] if a['formula'] is not None else 'n/a'}",
                  f"  irregularity: {percent(a['irregularity'])}", f"  status:       {a['status']}"]
    lines += ["", f"selected variables: {names(dr['selected_variables'])}",
              f"final formula:      {dr['final_formula'] if dr['final_formula'] is not None else 'n/a'}",
              f"final irregularity: {percent(dr['final_irregularity'])}"]
    if "search" in result:
        search = result["search"]
        if search.get("best_attempt") is not None:
            lines.append(f"best attempt:       {search['best_attempt']}")
        lines += ["", f"irregularity target: <{percent(search['target_irregularity'])}",
                  f"target met:         {'yes' if search['target_met'] else 'no'}",
                  f"search stopped:     {search['stop_reason']}",
                  f"attempts used:      {search['attempts_used']}/{search['max_attempts']}"]
    if "comparison" in result:
        lines += ["", f"ground truth: {names(result['ground_truth'])}"]
        for label, c in result["comparison"].items():
            lines.append(f"{label}: exact_match={str(c['exact_match']).lower()} "
                         f"missing={names(c['missing'])} extra={names(c['extra'])}")
    return "\n".join(lines)
