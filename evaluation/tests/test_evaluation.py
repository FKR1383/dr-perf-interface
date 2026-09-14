"""Run with python3 -m unittest discover -s evaluation/tests -v (no API calls)."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evaluation import codex_runner, drperf_measure as measurement, run
from evaluation.results import EvaluationError, comparison, summary, validate_result, write_json


def fitted(attempt=1, names=None, formula="4*n + 20", irregularity=0.00123, status="ok"):
    return {"attempt": attempt, "variables": ["n"] if names is None else names,
            "formula": formula, "irregularity": irregularity, "status": status}


def result(attempts=None, selected=0):
    attempts = [fitted()] if attempts is None else attempts
    final = attempts[selected]
    return {"attempts": attempts, "selected_variables": final["variables"],
            "final_formula": final["formula"], "final_irregularity": final["irregularity"]}


def raw_run(command, out):
    """Small real reader/derive input: one affine block and four state points."""
    out = Path(out)
    out.mkdir(parents=True)
    filename = "run.1.json"
    write_json(out / filename, {"drperf": {}, "regions": []})
    (out / (filename + ".slots")).write_text('0 "app" 0 "work"\n')
    (out / (filename + ".blocks")).write_text("".join(
        f'K {i} "parse" 1 "n" {n} "parse" 1\n0 {4*n+20}\n'
        for i, n in enumerate((100, 200, 300, 500))))
    return 0, "workload finished", [filename]


class ResultsTests(unittest.TestCase):
    def test_static_normalization_and_empty_set(self):
        self.assertEqual(validate_result({"variables": ["z", "n", "z"]}, "agent_only"),
                         {"variables": ["n", "z"]})
        self.assertEqual(validate_result({"variables": []}, "agent_only"), {"variables": []})

    def test_reject_malformed_static(self):
        for value in ({}, {"variables": "n"}, {"variables": [1]}, {"variables": [""]},
                      {"variables": [" n"]}, {"variables": [], "explanation": "none"}):
            with self.subTest(value=value), self.assertRaises(EvaluationError):
                validate_result(value, "agent_only")

    def test_experimental_normalization_and_nonlast_selection(self):
        first = fitted(names=["z", "n", "z"])
        second = fitted(attempt=2, irregularity=0.5)
        parsed = validate_result(result([first, second]), "agent_drperf", 2)
        self.assertEqual(parsed["selected_variables"], ["n", "z"])
        self.assertEqual(parsed["final_irregularity"], 0.00123)

    def test_reject_incomplete_or_fabricated_results(self):
        cases = [{"attempts": [], "selected_variables": [],
                  "final_formula": None, "final_irregularity": None}]
        for change in ({"attempt": 2}, {"attempt": True}, {"irregularity": "0%"},
                       {"irregularity": -0.1}, {"irregularity": 1.1}, {"irregularity": float("nan")},
                       {"irregularity": True}, {"formula": None}, {"status": "invented"},
                       {"variables": ["a", "b", "c", "d", "e"]}):
            cases.append(result([{**fitted(), **change}]))
        mismatch = result()
        mismatch["selected_variables"] = ["invented"]
        cases.append(mismatch)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(EvaluationError):
                validate_result(value, "agent_drperf")
        with self.assertRaisesRegex(EvaluationError, "limit"):
            validate_result(result([fitted(), fitted(attempt=2)]), "agent_drperf", 1)

    def test_failure_is_not_zero(self):
        attempt = fitted(formula=None, irregularity=None, status="insufficient_state_variation")
        self.assertIsNone(validate_result(result([attempt]), "agent_drperf")["final_irregularity"])
        attempt["irregularity"] = 0
        with self.assertRaisesRegex(EvaluationError, "failed measurement"):
            validate_result(result([attempt]), "agent_drperf")

    def test_summary_and_ground_truth(self):
        failed = fitted(attempt=2, names=[], formula=None, irregularity=None, status="workload_failed")
        data = {"agent_only": {"variables": []}, "agent_drperf": result([fitted(), failed])}
        text = summary(data)
        self.assertIn("variables: {}", text)
        self.assertIn("irregularity: 0.123%", text)
        self.assertIn("irregularity: n/a", text)
        self.assertIn("status:       workload_failed", text)
        self.assertEqual(comparison(["n", "other"], ["n", "entries"]),
                         {"exact_match": False, "missing": ["entries"], "extra": ["other"]})
        self.assertTrue(comparison([], [])["exact_match"])
        self.assertTrue(comparison(["n", "n"], ["n"])["exact_match"])


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_real_reader_and_derive(self):
        raw_run([], self.directory / "raw")
        value = measurement.analyze(self.directory / "raw", "parse", ["n"])
        self.assertEqual(value["formula"], "4*n + 20")
        self.assertEqual(value["irregularity"], 0)
        self.assertEqual(value["status"], "ok")
        self.assertEqual(measurement.analyze(self.directory / "raw", "missing", ["n"])["status"],
                         "region_not_reached")
        self.assertEqual(measurement.analyze(self.directory / "raw", "parse", ["alias"])["status"],
                         "state_mismatch")

    def test_invalid_and_insufficient_variation(self):
        raw_run([], self.directory / "raw")
        data = self.directory / "raw" / "run.1.json"
        write_json(data, {"drperf": {"unmatched_ends": 1}})
        self.assertIsNone(measurement.analyze(data.parent, "parse", ["n"])["irregularity"])
        write_json(data, {"drperf": {}})
        (data.parent / "run.1.json.blocks").write_text('K 0 "parse" 0 "parse" 10\n0 1000\n')
        value = measurement.analyze(data.parent, "parse", [])
        self.assertEqual(value["status"], "insufficient_state_variation")
        self.assertIsNone(value["formula"])
        self.assertIsNone(value["irregularity"])

    def test_exact_small_share_and_calibration(self):
        raw_run([], self.directory / "raw")
        regime = measurement.derive.Regime([(1,), (2,), (3,)], 1)
        regime.a = [4]
        regime.c = 1000
        regime.irr = {(1,): 1, (2,): 2, (3,): 3}
        with patch.object(measurement.derive, "derive", return_value=[regime]), \
             patch.object(measurement.runner, "marker_cost", return_value=(10, 0)):
            value = measurement.analyze(self.directory / "raw", "parse", ["n"])
        self.assertEqual(value["irregularity"], regime.irr_share())
        self.assertGreater(value["irregularity"], 0)
        self.assertLess(value["irregularity"], 0.05)
        self.assertEqual(value["formula"], "4*n + 990")

    def test_split_regimes_use_total_cost_ratio(self):
        raw_run([], self.directory / "raw")
        low = measurement.derive.Regime([(1,), (2,), (3,)], 1)
        high = measurement.derive.Regime([(10,), (20,), (30,)], 1)
        low.c, high.c = 100, 1000
        low.irr, high.irr = {(1,): 10}, {(10,): 1}
        with patch.object(measurement.derive, "derive", return_value=[low, high]):
            value = measurement.analyze(self.directory / "raw", "parse", ["n"])
        self.assertEqual(value["irregularity"], 11 / 3311)
        self.assertEqual(len(value["details"]["regimes"]), 2)
        self.assertIn("n <= 3", value["formula"])

    def test_workload_failure_and_missing_build(self):
        with patch.object(measurement, "check_build"), \
             patch.object(measurement.runner, "run", return_value=(7, "failure", [])):
            value = measurement.measure(["program"], self.directory, "parse", [])
        self.assertEqual(value["status"], "workload_failed")
        self.assertIsNone(value["irregularity"])
        with patch.object(measurement, "check_build", side_effect=EvaluationError("build first")):
            self.assertEqual(measurement.measure([], self.directory, "parse", [])["status"],
                             "drperf_not_built")

    def test_journal_limit_and_reject_modified_measurement(self):
        config = {"workspace": str(Path.cwd()), "journal": str(self.directory / "journal"),
                  "region": "parse", "command": ["program"], "max_attempts": 1}
        with patch.object(measurement, "check_build"), \
             patch.object(measurement.runner, "run", side_effect=raw_run):
            measurement.attempt(config, ["n"])
        self.assertEqual(measurement.recorded_attempts(config)[0]["irregularity"], 0)
        with self.assertRaisesRegex(EvaluationError, "limit"):
            measurement.attempt(config, ["n"])
        path = Path(config["journal"]) / "attempt-001/measurement.json"
        data = json.loads(path.read_text())
        data["formula"] = "invented"
        write_json(path, data)
        with self.assertRaisesRegex(EvaluationError, "raw data"):
            measurement.recorded_attempts(config)

    def test_failed_and_unreadable_runs_remain_in_journal(self):
        config = {"workspace": str(Path.cwd()), "journal": str(self.directory / "journal"),
                  "region": "parse", "command": ["program"], "max_attempts": 2}
        with patch.object(measurement, "check_build"), \
             patch.object(measurement.runner, "run", return_value=(7, "failure", [])):
            measurement.attempt(config, [])
        with patch.object(measurement, "check_build"), \
             patch.object(measurement.runner, "run", side_effect=raw_run), \
             patch.object(measurement.runner, "load_runs", side_effect=ValueError("bad raw data")):
            measurement.attempt(config, ["n"])
            records = measurement.recorded_attempts(config)
        self.assertEqual([r["status"] for r in records], ["workload_failed", "measurement_error"])
        self.assertTrue(all(r["irregularity"] is None for r in records))


class HarnessTests(unittest.TestCase):
    def test_substituted_codex_isolation_and_measurement_reconciliation(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source, output, auth = base / "source", base / "results", base / "auth"
            source.mkdir()
            output.mkdir()
            auth.mkdir()
            (source / "app.py").write_text("original local edit")
            (source / "alias.py").symlink_to(source / "app.py")
            (source / ".git").write_text("gitdir: /original/history")
            (auth / "config.toml").write_text('model = "configured-model"\n')
            (auth / "history.jsonl").write_text("unrelated session")
            invocations = []

            def fake_codex(command, **kwargs):
                if "--help" in command:
                    return subprocess.CompletedProcess(command, 0, stdout="--output-schema --output-last-message --ephemeral")
                cwd = Path(kwargs["cwd"])
                control = Path(command[command.index("--output-last-message") + 1]).parent
                self.assertEqual((cwd / "app.py").read_text(), "original local edit")
                self.assertFalse((cwd / "alias.py").is_symlink())
                self.assertFalse((cwd / ".git").exists())
                self.assertEqual(list(output.iterdir()), [])
                private_home = Path(kwargs["env"]["CODEX_HOME"])
                self.assertFalse((private_home / "history.jsonl").exists())
                self.assertIn("configured-model", (private_home / "config.toml").read_text())
                self.assertIn("--ephemeral", command)
                self.assertNotIn("resume", command)
                self.assertIn('sandbox_workspace_write.writable_roots=[]', command)
                if not invocations:
                    self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
                    self.assertNotIn("measurement-config", kwargs["input"])
                    self.assertNotIn("Agent + Dr. Perf", kwargs["input"])
                    answer = {"variables": ["n", "n"]}
                else:
                    old_cwd, old_control, old_home = invocations[0]
                    for path in (old_cwd, old_control, old_home):
                        self.assertFalse(path.exists())
                    self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
                    self.assertNotIn("baseline-secret", kwargs["input"])
                    (cwd / "alias.py").write_text("temporary instrumentation")
                    config = json.loads((cwd.parent / "measurement-config.json").read_text())
                    self.assertEqual(config["command"], ["python3", str(cwd / "app.py")])
                    previous = Path.cwd()
                    try:
                        os.chdir(cwd)
                        with patch.object(measurement.runner, "run", side_effect=raw_run):
                            measurement.attempt(config, ["n"])
                    finally:
                        os.chdir(previous)
                    answer = result([fitted(formula="4*n + 20", irregularity=0)])
                invocations.append((cwd, control, private_home))
                kwargs["stdout"].write("baseline-secret" if len(invocations) == 1 else "experimental-log")
                write_json(control / "final.json", answer)
                return subprocess.CompletedProcess(command, 0)

            with patch.dict(os.environ, {"CODEX_HOME": str(auth)}), \
                 patch.object(codex_runner.shutil, "which", return_value="/fake/codex"), \
                 patch.object(codex_runner.subprocess, "run", side_effect=fake_codex), \
                 patch.object(measurement, "check_build"):
                value = run.evaluate(source, "parse", ["python3", str(source / "app.py")],
                                     output, ground_truth=["n", "entries"])
            self.assertEqual(len(invocations), 2)
            self.assertEqual((source / "app.py").read_text(), "original local edit")
            self.assertEqual(value["agent_only"], {"variables": ["n"]})
            self.assertEqual(value["comparison"]["agent_only"]["missing"], ["entries"])
            self.assertTrue((output / "result.json").is_file())
            self.assertFalse(any("auth.json" in str(p) for p in output.rglob("*")))
            self.assertEqual((output / "logs/agent_only/codex.log").read_text(), "baseline-secret")

    def test_invalid_codex_json_and_missing_cli(self):
        with patch.object(codex_runner.shutil, "which", return_value=None):
            with self.assertRaisesRegex(EvaluationError, "not installed"):
                codex_runner.find_codex()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "workspace"
            workspace.mkdir()

            def bad_output(command, **kwargs):
                Path(command[command.index("--output-last-message") + 1]).write_text("not JSON")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(codex_runner.subprocess, "run", side_effect=bad_output), \
                 self.assertRaisesRegex(EvaluationError, "invalid structured Codex output"):
                codex_runner.invoke("codex", "agent_only", workspace, root / "control", "inspect")

    def test_cli_errors_are_short(self):
        with tempfile.TemporaryDirectory() as temp:
            cases = [["--workspace", temp, "--region", "parse"],
                     ["--workspace", temp + "/missing", "--region", "parse", "--", "./app"],
                     ["--workspace", temp, "--region", "parse", "--max-attempts", "0", "--", "./app"]]
            for args in cases:
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(run.main(args), 1)
                self.assertIn("evaluation:", err.getvalue())
                self.assertNotIn("Traceback", err.getvalue())

    def test_cli_no_model_saves_summary_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            output, err = io.StringIO(), io.StringIO()
            failure = fitted(names=[], formula=None, irregularity=None, status="region_not_reached")
            value = {"region": "parse", "agent_only": {"variables": []},
                     "agent_drperf": result([failure])}
            with patch.object(run, "evaluate", return_value=value), \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(err):
                rc = run.main(["--workspace", temp, "--region", "parse",
                               "--results-dir", temp + "/results", "--", "./app"])
            self.assertEqual(rc, 1)
            self.assertIn("region_not_reached", output.getvalue())
            self.assertIn("no model selected", err.getvalue())


@unittest.skipUnless(os.environ.get("DRPERF_EVAL_INTEGRATION") == "1",
                     "set DRPERF_EVAL_INTEGRATION=1 for the built Dr. Perf integration test")
class NativeIntegrationTests(unittest.TestCase):
    def test_existing_affine_example(self):
        measurement.check_build()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            executable = directory / "affine"
            subprocess.run(["gcc", "-O2", "-o", str(executable),
                            str(measurement.ROOT / "examples/c_suite/c1_affine.c"),
                            "-L" + str(measurement.ROOT / "build"), "-lperfmark",
                            "-Wl,-rpath," + str(measurement.ROOT / "build")], check=True)
            value = measurement.measure([str(executable), "multi=1"], directory, "single", ["n"])
            self.assertEqual(value["status"], "ok", value)
            self.assertTrue(value["formula"].startswith("4*n + "), value)
            self.assertEqual(value["irregularity"], 0.0)


if __name__ == "__main__":
    unittest.main()
