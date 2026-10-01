from pathlib import Path
import json
import tempfile
import unittest

import aggregate_experiment


class AggregateExperimentTests(unittest.TestCase):
    def test_combines_available_suites_and_marks_missing_ones(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            suite = root / "accidental-quadratic"
            suite.mkdir()
            (suite / "full-report.json").write_text(json.dumps({
                "protocol": "example",
                "aggregate": {"cases": 1},
                "results": [{
                    "case": "aq-001",
                    "status": "success",
                    "iterations": 2,
                    "attempts": [{"irregularity_percent": 17.0},
                                 {"irregularity_percent": 3.0}],
                }],
            }))
            report = aggregate_experiment.write_reports(root)
            self.assertEqual(report["totals"]["reported_suites"], 1)
            self.assertEqual(report["totals"]["success"], 1)
            self.assertEqual(
                report["results"][0]["best_irregularity_percent"], 3.0
            )
            self.assertTrue((root / "experiment-report.md").is_file())
            self.assertTrue((root / "experiment-report.csv").is_file())


if __name__ == "__main__":
    unittest.main()
