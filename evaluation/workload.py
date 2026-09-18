"""Freeze workload files and permit explicitly bounded instrumentation edits."""
import ast
import hashlib
import json
from pathlib import Path

try:
    from .results import EvaluationError, read_json
except ImportError:
    from results import EvaluationError, read_json

MANIFEST = ".drperf-workload.json"
IGNORED = {".git", ".codex", ".eval-tmp", "__pycache__"}


class WorkloadChanged(EvaluationError):
    pass


def relative_name(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvaluationError("workload paths must be nonempty relative POSIX paths")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.as_posix() != value.rstrip("/"):
        raise EvaluationError(f"workload path must stay inside the workspace: {value!r}")
    if any(part in IGNORED for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
        raise EvaluationError(f"workload path is excluded from snapshots: {value!r}")
    return value


def paths(value):
    if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
        raise EvaluationError("workload file lists must be arrays of relative paths")
    return [relative_name(p) for p in value]


def matches(name, patterns):
    return any(name == p or p.endswith("/") and name.startswith(p) for p in patterns)


def command_list(value):
    if not isinstance(value, list) or any(not isinstance(p, str) or not p for p in value):
        raise EvaluationError("workload build must be an argument array (or []), not a shell string")
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


class PythonMarker(ast.NodeTransformer):
    """Ignore only state keyword arguments on the existing target marker."""
    def __init__(self, region):
        self.region = region
        self.count = 0

    def visit_Call(self, node):
        if (isinstance(node.func, ast.Attribute) and node.func.attr == "region"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "perfmark"
                and len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == self.region):
            self.count += 1
            node.keywords = []
        return self.generic_visit(node)


def source_fingerprint(path, rule, region):
    text = path.read_text()
    if rule == {"kind": "python-marker"}:
        normalizer = PythonMarker(region)
        tree = normalizer.visit(ast.parse(text))
        if normalizer.count != 1:
            raise WorkloadChanged(f"{path.name}: expected exactly one perfmark.region({region!r}) marker")
        return digest(ast.dump(tree, include_attributes=False).encode())
    if isinstance(rule, dict) and set(rule) == {"kind", "start", "end"} and rule["kind"] == "text-block":
        start, end = rule["start"], rule["end"]
        if not all(isinstance(v, str) and v for v in (start, end)) or start == end:
            raise EvaluationError("instrumentation block anchors must be distinct nonempty strings")
        if text.count(start) != 1 or text.count(end) != 1:
            raise WorkloadChanged(f"{path.name}: instrumentation block anchors must each occur once")
        left, right = text.index(start) + len(start), text.index(end)
        if left > right:
            raise WorkloadChanged(f"{path.name}: instrumentation block anchors are reversed")
        return digest((text[:left] + text[right:]).encode())
    raise EvaluationError(f"unsupported instrumentation rule for {path.name}: {rule!r}")


class FrozenWorkload:
    @classmethod
    def from_metadata(cls, metadata, region):
        instance = cls.__new__(cls)
        instance.region = region
        instance.instrumentation = metadata["instrumentation"]
        instance.build = metadata["build"]
        instance.outputs = metadata["build_outputs"]
        instance.input_trace = metadata["input_trace"]
        instance.reference = metadata["protected_file_sha256"]
        return instance

    def __init__(self, snapshot, region):
        self.snapshot, self.region = Path(snapshot), region
        if (self.snapshot / MANIFEST).is_file():
            definition = read_json(self.snapshot / MANIFEST)
            allowed = {"version", "instrumentation", "build", "build_outputs", "input_trace"}
            if not isinstance(definition, dict) or set(definition) - allowed or definition.get("version") != 1:
                raise EvaluationError(f"{MANIFEST}: expected version 1 workload definition")
            self.origin = MANIFEST
        elif (self.snapshot / "case.json").is_file():
            case = read_json(self.snapshot / "case.json")
            if (case.get("language") != "python" or case.get("marker", {}).get("name") != region
                    or not case.get("tests", {}).get("files")):
                raise EvaluationError(f"this export needs {MANIFEST} declaring its instrumentation and build")
            for name in paths(case["tests"]["files"]):
                if not (self.snapshot / name).is_file():
                    raise EvaluationError(f"missing workload asset: {name}")
            definition = {"version": 1, "instrumentation": {
                case["source"]["path"]: {"kind": "python-marker"}}}
            self.origin = "case.json"
        else:
            raise EvaluationError(f"missing workload definition: add {MANIFEST}; see evaluation/README.md. "
                                  "The harness must know which edits are instrumentation before comparing workloads.")
        self.instrumentation = definition.get("instrumentation")
        if not isinstance(self.instrumentation, dict) or not self.instrumentation:
            raise EvaluationError("workload definition needs a nonempty instrumentation mapping")
        for name in self.instrumentation:
            relative_name(name)
            if not (self.snapshot / name).is_file():
                raise EvaluationError(f"missing instrumentation source: {name}")
        self.build = command_list(definition.get("build", []))
        self.outputs = paths(definition.get("build_outputs", []))
        if bool(self.outputs) != bool(self.build):
            raise EvaluationError("build and build_outputs must be declared together")
        self.input_trace = definition.get("input_trace")
        if self.input_trace is not None:
            relative_name(self.input_trace)
            if self.input_trace.endswith("/"):
                raise EvaluationError("input_trace must name a file")
        for name in [MANIFEST, "case.json", *self.instrumentation,
                     *(str(Path(arg)) for arg in self.build[:1])]:
            if matches(name, self.outputs) or name == self.input_trace:
                raise EvaluationError(f"protected file overlaps a generated output: {name}")
        self.reference = self.fingerprints(self.snapshot)
        self.trace_reference = None
        self.metadata = {"definition": self.origin, "policy": "frozen_files_and_bounded_instrumentation",
                         "sha256": digest(json.dumps(self.reference, sort_keys=True).encode()),
                         "protected_file_sha256": self.reference,
                         "instrumentation": self.instrumentation, "build": self.build,
                         "build_outputs": self.outputs, "input_trace": self.input_trace}

    def fingerprints(self, workspace):
        records = {}
        for path in sorted(Path(workspace).rglob("*")):
            relative = path.relative_to(workspace)
            if any(p in IGNORED for p in relative.parts) or path.suffix in {".pyc", ".pyo"}:
                continue
            name = relative.as_posix()
            if matches(name, self.outputs) or name == self.input_trace:
                continue
            if path.is_symlink():
                raise WorkloadChanged(f"workload file became a symlink: {name}")
            if path.is_file():
                try:
                    records[name] = (source_fingerprint(path, self.instrumentation[name], self.region)
                                     if name in self.instrumentation else file_digest(path))
                except (SyntaxError, UnicodeError) as exc:
                    raise WorkloadChanged(f"invalid instrumentation source {name}: {exc}") from exc
        return records

    def validate(self, workspace):
        actual = self.fingerprints(workspace)
        changed = sorted(k for k in self.reference.keys() | actual.keys()
                         if self.reference.get(k) != actual.get(k))
        if changed:
            raise WorkloadChanged("workload/source changed outside permitted instrumentation: " + ", ".join(changed[:10]))

    def validate_trace(self, workspace):
        if self.input_trace is None:
            return None
        path = Path(workspace) / self.input_trace
        try:
            records = read_json(path)
        except EvaluationError as exc:
            raise WorkloadChanged(f"workload did not produce its input trace: {self.input_trace}") from exc
        if not isinstance(records, list) or not records:
            raise WorkloadChanged("input_trace must contain a nonempty JSON array of actual inputs in call order")
        try:
            encoded = json.dumps(records, sort_keys=True, allow_nan=False).encode()
        except ValueError as exc:
            raise WorkloadChanged("input_trace must contain finite JSON values") from exc
        if self.trace_reference is None:
            self.trace_reference = encoded
        elif encoded != self.trace_reference:
            raise WorkloadChanged("actual workload inputs/call order differ from the first measurement")
        return {"sha256": digest(encoded), "records": len(records)}
