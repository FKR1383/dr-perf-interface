"""Regression tests for the shared baseline/experimental execution context."""
import json
import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evaluation import baseline_measure, codex_runner, drperf_measure
from evaluation.measurement_session import MeasurementSession
from evaluation.results import EvaluationError, read_json, write_json
from evaluation.workload import FrozenWorkload


class SessionTests(unittest.TestCase):
    def test_frozen_environment_paths_and_reset_with_different_submitters(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original, first, second = (root / name for name in ("original", "first", "second"))
            for source in (original, first, second):
                source.mkdir()
                (source / "app.py").write_text("pass\n")
                (source / "__pycache__").mkdir()
                (source / "__pycache__/app.pyc").write_bytes(b"stale bytecode")
                (source / "loose.pyc").write_bytes(b"stale bytecode")
                (source / ".eval-tmp").mkdir()
                (source / ".eval-tmp/agent-data").write_text("private")
            with patch.dict(os.environ, {"PYTHONPATH": str(original), "TEST_SETTING": "frozen"}):
                session = MeasurementSession(root / "runtime", original)
            calls = []

            def worker(command, **kwargs):
                calls.append((command, kwargs["cwd"], dict(kwargs["env"])))
                self.assertEqual(kwargs["env"]["TEST_SETTING"], "frozen")
                self.assertEqual(kwargs["env"]["PYTHONPATH"], str(session.workspace))
                self.assertEqual(kwargs["env"]["PYTHONHASHSEED"], "0")
                self.assertFalse(list(session.workspace.rglob("*.pyc")))
                self.assertFalse((session.workspace / ".eval-tmp").exists())
                self.assertFalse((session.workspace / "previous-run").exists())
                for name in ("cache", "tmp"):
                    self.assertEqual(list((session.root / name).iterdir()), [])
                    (session.root / name / "previous-run").touch()
                (session.workspace / "previous-run").touch()
                request = read_json(session.root / "request.json")
                self.assertEqual(request["command"], ["python3", str(session.workspace / "app.py"),
                                                     "--root=" + str(session.workspace)])
                write_json(session.root / "result.json", drperf_measure.failed("region_not_reached", "test"))
                return subprocess.CompletedProcess(command, 0, stdout="worker output")

            with patch("evaluation.measurement_session.subprocess.run", side_effect=worker):
                for index, source in enumerate((first, second)):
                    with patch.dict(os.environ, {"TEST_SETTING": str(index), "PYTHONHASHSEED": "random"}):
                        measured = session.measure(source, ["python3", str(source / "app.py"),
                                                            "--root=" + str(source)],
                                                   root / f"out-{index}", "parse", ["n"])
                    self.assertEqual(measured["status"], "region_not_reached")
                    self.assertFalse(session.root.exists())
            self.assertEqual(calls[0], calls[1])
            first_controls = read_json(root / "out-0/execution.json")
            self.assertEqual(first_controls, read_json(root / "out-1/execution.json"))
            self.assertEqual(set(first_controls["file_sha256"]), {"app.py"})
            self.assertNotIn("frozen", json.dumps(first_controls))

    def test_worker_failure_preserves_diagnostics_and_cleans_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            session = MeasurementSession(root / "runtime", source)
            with patch.object(session, "_run_worker", return_value=subprocess.CompletedProcess([], 7, "failure detail")):
                value = session.measure(source, ["program"], root / "out", "region", ["n"])
            self.assertEqual(value["status"], "measurement_error")
            self.assertEqual((root / "out/launcher.log").read_text(), "failure detail")
            self.assertFalse(session.root.exists())

    def test_service_errors_are_published_without_running_local_measurement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / "journal"
            journal.mkdir()
            config = {"workspace": str(Path.cwd()), "journal": str(journal), "region": "parse",
                      "command": ["program"], "max_attempts": 2, "measurement_service": True}
            session = MeasurementSession(root / "runtime", Path.cwd())
            with patch.object(session, "measure", side_effect=OSError("worker unavailable")), \
                 patch.object(drperf_measure, "measure", side_effect=AssertionError("local execution forbidden")), \
                 session.serve(config):
                for number in (1, 2):
                    value = drperf_measure.attempt(config, ["n"])
                    self.assertEqual(value["attempt"], number)
                    self.assertEqual(value["status"], "measurement_error")
                    self.assertIn("worker unavailable", value["details"]["message"])
                self.assertEqual(len(drperf_measure.recorded_attempts(config)), 2)
                with self.assertRaisesRegex(EvaluationError, "limit"):
                    drperf_measure.attempt(config, ["n"])
            self.assertFalse((journal / ".service-active").exists())

    def test_missing_service_fails_instead_of_launching_locally(self):
        with tempfile.TemporaryDirectory() as temp:
            config = {"workspace": str(Path.cwd()), "journal": temp, "region": "parse",
                      "command": ["program"], "max_attempts": 1, "measurement_service": True}
            with patch.object(drperf_measure, "measure") as local, \
                 self.assertRaisesRegex(EvaluationError, "service is not running"):
                drperf_measure.attempt(config, ["n"])
            local.assert_not_called()


@unittest.skipUnless(os.environ.get("DRPERF_EVAL_INTEGRATION") == "1",
                     "set DRPERF_EVAL_INTEGRATION=1 for the aq-001 controlled measurement regression")
class NativeSessionTests(unittest.TestCase):
    def test_generic_c_workspace_uses_fixed_build_and_inputs(self):
        drperf_measure.check_build()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "driver.c").write_text('''#include "perfmark.h"
volatile unsigned long total;
int main(void) {
    const int inputs[] = {100, 200, 300, 500};
    for (int c = 0; c < 4; ++c) {
        int n = inputs[c];
        /* STATES BEGIN */
        perfmark_begin("work", "n", n);
        /* STATES END */
        for (int i = 0; i < n; ++i) total += i;
        perfmark_end("work");
    }
    return 0;
}
''')
            repository = drperf_measure.ROOT
            build = ["cc", "-O2", "-I" + str(repository / "perfmark"), "driver.c",
                     "-L" + str(repository / "build"), "-lperfmark",
                     "-Wl,-rpath," + str(repository / "build"), "-o", "program"]
            write_json(source / ".drperf-workload.json", {"version": 1, "instrumentation": {
                "driver.c": {"kind": "text-block", "start": "/* STATES BEGIN */", "end": "/* STATES END */"}},
                "build": build, "build_outputs": ["program"]})
            session = MeasurementSession(root / "runtime", source, FrozenWorkload(source, "work"), ["./program"])
            first = session.measure(source, ["./program"], root / "first", "work", ["n"])
            self.assertEqual(first["status"], "ok", first)
            # This must be discarded and rebuilt, even though the agent could
            # have supplied an executable with different assignments or flags.
            (source / "program").write_text("untrusted build product")
            second = session.measure(source, ["./program"], root / "second", "work", ["n"])
            self.assertEqual(second["status"], "ok", second)
            self.assertEqual(first, second)
            for label in ("first", "second"):
                check = read_json(root / label / "workload-check.json")
                self.assertEqual(check["region_calls"], 4)
                self.assertEqual(check["status"], "ok")

    def test_aq001_equal_raw_counts_despite_helper_environment_and_bytecode_changes(self):
        from benchmarks.regions import collect
        from evaluation.reproduce_aq001 import COMMAND, FEATURE, REGION, prepare

        drperf_measure.check_build()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clean, source = root / "clean", root / "source"
            case = next(path for path in collect.cases() if collect.load(path)["id"] == REGION)
            collect.export(case, clean)
            shutil.copytree(clean, source)
            session = MeasurementSession(root / "runtime", clean, FrozenWorkload(clean, REGION), COMMAND)

            def instrument(*args, **kwargs):
                prepared = root / "prepared"
                prepare(clean, prepared)
                shutil.copyfile(prepared / "Lib/enum.py", source / "Lib/enum.py")
                return {"status": "ready", "reason": "", "advice": "", "bindings": [
                    {"variable": FEATURE, "expression": FEATURE, "location": "Lib/enum.py:206"}]}

            with patch.object(codex_runner, "invoke", side_effect=instrument):
                baseline = baseline_measure.measure("codex", source, root / "control", root / "baseline",
                                                    REGION, COMMAND, [FEATURE], measurement_session=session)
            self.assertEqual(baseline["status"], "ok", baseline)
            journal = root / "journal"
            journal.mkdir()
            config = {"workspace": str(source), "journal": str(journal), "region": REGION,
                      "command": COMMAND, "max_attempts": 2, "measurement_service": True}
            write_json(root / "config.json", config)
            helper = [sys.executable, str(drperf_measure.HERE / "drperf_measure.py"),
                      "--config", str(root / "config.json"), "--variables-json", json.dumps([FEATURE])]
            with session.serve(config):
                for index in (1, 2):
                    # Extra environment entries changed native counts before the
                    # shared service. Precompiled bytecode must not leak either.
                    py_compile.compile(str(source / "Lib/enum.py"), doraise=True)
                    env = dict(os.environ, PYTHONHASHSEED="random", OMP_NUM_THREADS=str(index + 7))
                    env.update({f"DRPERF_DIAGNOSTIC_UNUSED_{j}": "padding" for j in range(16 * index)})
                    completed = subprocess.run(helper, cwd=source, env=env, text=True,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                    self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
                    value = json.loads(completed.stdout)
                    self.assertEqual(value["formula"], baseline["formula"])
                    self.assertEqual(value["irregularity"], baseline["irregularity"])
            controls = read_json(root / "baseline/execution.json")

            def calls(out):
                raw = drperf_measure.runner.load_runs(str(out / "raw"))
                return [(r["state"], r["self"]) for r in drperf_measure.runner.load_traces_all(raw)
                        if r["region"] == REGION]

            reference = calls(root / "baseline")
            self.assertEqual(len(reference), 37)
            for index in (1, 2):
                out = journal / f"attempt-{index:03d}"
                self.assertEqual(read_json(out / "execution.json"), controls)
                self.assertEqual(calls(out), reference)
            self.assertEqual(len(drperf_measure.recorded_attempts(config)), 2)
