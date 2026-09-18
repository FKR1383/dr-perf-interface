"""One harness-owned execution context for both competitors' measurements.

Agents submit candidates through their journal. They never launch the measured
workload themselves. A fresh worker uses the same paths and frozen environment
for every request, independently of the submitting agent's shell environment.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading

try:
    from . import drperf_measure
    from .results import EvaluationError, read_json, variables, write_json
    from .workload import WorkloadChanged
except ImportError:
    import drperf_measure
    from results import EvaluationError, read_json, variables, write_json
    from workload import WorkloadChanged

HERE = Path(__file__).resolve().parent
IGNORE = shutil.ignore_patterns(".git", ".codex", ".eval-tmp", "__pycache__", "*.pyc", "*.pyo")


def rebase_command(command, source, destination):
    def rebase(arg):
        if arg == str(source) or arg.startswith(str(source) + os.sep):
            return str(destination) + arg[len(str(source)):]
        if "=" in arg:
            key, value = arg.split("=", 1)
            if value == str(source) or value.startswith(str(source) + os.sep):
                return key + "=" + str(destination) + value[len(str(source)):]
        return arg
    return [rebase(arg) for arg in command]


def file_hashes(workspace):
    result = {}
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            result[str(path.relative_to(workspace))] = digest.hexdigest()
    return result


class MeasurementSession:
    def __init__(self, root, source, workload=None, command=None):
        self.root = Path(root)
        self.workspace = self.root / "workspace"
        self.out = self.root / "measurement"
        self.workload = workload
        self.call_count = None
        self.state_values = {}
        self.command = rebase_command(command, source, self.workspace) if command is not None else None
        self.environment = dict(os.environ)
        # Rebase path entries from the original workspace once, never from an
        # agent's environment. Keep user library/venv settings and tool scope.
        for key in ("PATH", "PYTHONPATH", "LD_LIBRARY_PATH"):
            if key in self.environment:
                self.environment[key] = os.pathsep.join(rebase_command(
                    self.environment[key].split(os.pathsep), source, self.workspace))
        self.environment.update({
            "PWD": str(self.workspace), "TMPDIR": str(self.root / "tmp"),
            "TMP": str(self.root / "tmp"), "TEMP": str(self.root / "tmp"),
            "XDG_CACHE_HOME": str(self.root / "cache"), "PYTHONHASHSEED": "0",
            "PYTHONPYCACHEPREFIX": str(self.root / "cache/bytecode"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.environment.pop("OLDPWD", None)
        self.environment = dict(sorted(self.environment.items()))
        self.protocol = {
            "launcher": "harness_worker", "workspace": str(self.workspace),
            "raw_output": str(self.out / "raw"),
            "environment_sha256": hashlib.sha256(json.dumps(
                self.environment, sort_keys=True).encode()).hexdigest(),
            "preparation": "fresh process; fresh workspace, temporary and cache directories; no Python bytecode caches",
            "scope": {key: self.environment.get(key, default) for key, default in (
                ("DRPERF_FOLLOW_THREADS", "1"), ("DRPERF_EXCLUDE_CUDA_MODULE", ""),
                ("OMP_NUM_THREADS", "4"), ("MKL_NUM_THREADS", "4"), ("OPENBLAS_NUM_THREADS", "4"))},
        }

        if workload is not None:
            self.protocol["workload"] = workload.metadata

    def _run_worker(self):
        return subprocess.run(
            [sys.executable, str(HERE / "measurement_worker.py"), str(self.root / "request.json")],
            cwd=self.workspace, env=self.environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def validate_states(self, out, region):
        raw = drperf_measure.runner.load_runs(str(out / "raw"))
        calls = [r["state"] for r in drperf_measure.runner.load_traces_all(raw) if r["region"] == region]
        if not calls:
            return None
        if self.call_count is not None and len(calls) != self.call_count:
            raise WorkloadChanged("number of target-region calls changed under the frozen workload")
        names = set.intersection(*(set(call) for call in calls))
        values = {name: [call[name] for call in calls] for name in names}
        if any(self.state_values[name] != values[name] for name in values.keys() & self.state_values.keys()):
            raise WorkloadChanged("recorded values of a shared feature changed in target-region call order")
        self.call_count = len(calls)
        self.state_values.update(values)
        return len(calls)

    def measure(self, source, command, out, region, candidate):
        """Measure an instrumented copy; retain no baseline files between calls."""
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        try:
            if self.workload is not None:
                self.workload.validate(source)
            shutil.copytree(source, self.workspace, ignore=IGNORE, symlinks=False)
            for path in (self.out, self.root / "tmp", self.root / "cache"):
                path.mkdir()
            command = rebase_command(command, source, self.workspace)
            if self.command is not None and command != self.command:
                raise WorkloadChanged("workload command or its arguments changed")
            if self.workload is not None:
                if region != self.workload.region:
                    raise WorkloadChanged("target region changed")
                self.workload.validate(self.workspace)
                # Rebuild with the frozen command, never trust agent-built products.
                for name in self.workload.outputs + ([self.workload.input_trace] if self.workload.input_trace else []):
                    path = self.workspace / name
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink(missing_ok=True)
            controls = {**self.protocol, "command": command, "file_sha256": file_hashes(self.workspace)}
            write_json(out / "execution.json", controls)
            write_json(self.root / "request.json", {
                "command": command, "out": str(self.out), "region": region, "variables": candidate,
                "workload": self.workload.metadata if self.workload is not None else None})
            completed = self._run_worker()
            (self.out / "launcher.log").write_text(completed.stdout or "")
            shutil.copytree(self.out, out, dirs_exist_ok=True)
            if completed.returncode:
                return drperf_measure.failed("measurement_error", "measurement worker failed; see launcher.log")
            result = read_json(self.root / "result.json")
            if self.workload is not None:
                self.workload.validate(self.workspace)
                if (out / "workload-check.json").exists():
                    return result
                trace = self.workload.validate_trace(self.workspace) if (out / "process.json").exists() else None
                calls = self.validate_states(out, region) if result["status"] == "ok" else None
                write_json(out / "workload-check.json", {
                    "status": "ok", "workload_sha256": self.workload.metadata["sha256"],
                    "input_trace": trace, "region_calls": calls})
                if trace is not None:
                    shutil.copyfile(self.workspace / self.workload.input_trace, out / "workload-inputs.json")
            return result
        except WorkloadChanged as exc:
            write_json(out / "workload-check.json", {"status": "rejected", "message": str(exc)})
            return drperf_measure.failed("invalid_measurement", str(exc))
        except (OSError, ValueError, EvaluationError) as exc:
            return drperf_measure.failed("measurement_error", str(exc))
        finally:
            # The next agent must not be able to inspect a previous baseline.
            shutil.rmtree(self.root, ignore_errors=True)

    @contextmanager
    def serve(self, config):
        """Service synchronous helper requests while Codex is running."""
        journal = Path(config["journal"])
        active = journal / ".service-active"
        active.touch()
        stopped = threading.Event()

        def worker():
            try:
                for index in range(1, min(config["max_attempts"], drperf_measure.MAX_ATTEMPTS) + 1):
                    out = journal / f"attempt-{index:03d}"
                    while not (out / ".request-ready").exists():
                        if stopped.wait(0.05):
                            return
                    candidate = []
                    try:
                        candidate = variables(read_json(out / "request.json")["variables"])
                        measured = self.measure(Path(config["workspace"]), config["command"], out,
                                                config["region"], candidate)
                    except Exception as exc:
                        measured = drperf_measure.failed("measurement_error", str(exc))
                    record = {"attempt": index, "variables": candidate, **measured}
                    # Publish only once all raw artifacts and JSON are complete.
                    write_json(out / ".measurement-pending.json", record)
                    (out / ".measurement-pending.json").replace(out / "measurement.json")
            finally:
                active.unlink(missing_ok=True)

        thread = threading.Thread(target=worker, name="evaluation-measurements", daemon=True)
        thread.start()
        try:
            yield
        finally:
            stopped.set()
            thread.join()
            active.unlink(missing_ok=True)
