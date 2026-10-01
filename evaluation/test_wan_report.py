import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

import wan_report


def summary(case, status, iterations, attempts, success_iteration=None):
    return {
        "schema_version": 1,
        "case_id": case,
        "status": status,
        "threshold_percent": 10.0,
        "comparison": "strictly-less-than",
        "iterations_evaluated": iterations,
        "success_iteration": success_iteration,
        "attempts": attempts,
    }


def attempt(iteration, pcvs, outcome, irregularity):
    return {
        "iteration": iteration,
        "pcvs": pcvs,
        "outcome": outcome,
        "irregularity_percent": irregularity,
        "measurement_runs": 1,
    }


class WanReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, directory, value):
        path = self.root / directory / "summary.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(value))

    def test_collects_sorts_and_preserves_every_attempt(self):
        self.put("second", summary(
            "wan-010", "success", 2,
            [
                attempt(1, ["frames"], "retry", 22.25),
                attempt(2, ["frames", "frames * height * width"], "success", 7.5),
            ],
            success_iteration=2,
        ))
        self.put("first", summary(
            "wan-002", "exhausted", 2,
            [
                attempt(1, ["height"], "retry", 15.0),
                attempt(2, ["height", "width"], "retry", 11.125),
            ],
        ))

        report = wan_report.collect(self.root)

        self.assertEqual([row["case"] for row in report["cases"]], ["wan-002", "wan-010"])
        success = report["cases"][1]
        self.assertEqual(success["iterations"], 2)
        self.assertEqual(len(success["attempts"]), 2)
        self.assertEqual(success["attempts"][0]["pcvs"], ["frames"])
        self.assertEqual(success["attempts"][0]["irregularity_percent"], 22.25)
        self.assertEqual(success["final_pcvs"], ["frames", "frames * height * width"])
        self.assertEqual(
            success["final_result"],
            {"outcome": "success", "irregularity_percent": 7.5},
        )
        exhausted = report["cases"][0]
        self.assertEqual(exhausted["final_pcvs"], ["height", "width"])
        self.assertEqual(exhausted["final_result"]["outcome"], "retry")

    def test_pending_and_measurement_error_have_null_results(self):
        self.put("pending", summary("wan-001", "awaiting-selector", 0, []))
        self.put("error", summary(
            "wan-003", "measurement-error", 0,
            [attempt(1, ["n"], "measurement-error", None)],
        ))

        rows = wan_report.collect(self.root)["cases"]

        self.assertEqual(rows[0]["final_pcvs"], [])
        self.assertEqual(
            rows[0]["final_result"],
            {"outcome": "pending", "irregularity_percent": None},
        )
        self.assertEqual(rows[1]["status"], "measurement-error")
        self.assertEqual(rows[1]["iterations"], 0)
        self.assertEqual(rows[1]["final_pcvs"], ["n"])
        self.assertIsNone(rows[1]["final_result"]["irregularity_percent"])

    def test_csv_and_markdown_are_result_only_tables(self):
        self.put("case", summary(
            "wan-004", "success", 1,
            [attempt(1, ["rows|columns", "batch"], "success", 9.875)],
            success_iteration=1,
        ))
        report = wan_report.collect(self.root)

        csv_rows = list(csv.DictReader(io.StringIO(wan_report.render_csv(report))))
        self.assertEqual(list(csv_rows[0]), list(wan_report.FIELDNAMES))
        self.assertEqual(csv_rows[0]["case"], "wan-004")
        self.assertIn("rows|columns", csv_rows[0]["attempts"])
        self.assertEqual(csv_rows[0]["final_result"], "success|9.875%")

        markdown = wan_report.render_markdown(report)
        self.assertTrue(markdown.startswith("| case | status | iterations |"))
        self.assertIn("rows\\|columns", markdown)
        self.assertNotIn("# ", markdown)

    def test_write_reports_creates_all_formats(self):
        self.put("case", summary("wan-005", "awaiting-measurement", 0, [
            attempt(1, ["frames"], "pending", None),
        ]))
        output = self.root / "reports"

        report = wan_report.write_reports(self.root, output)

        self.assertEqual(json.loads((output / "wan-report.json").read_text()), report)
        self.assertIn("wan-005", (output / "wan-report.csv").read_text())
        self.assertIn("wan-005", (output / "wan-report.md").read_text())

    def test_duplicate_case_is_rejected(self):
        value = summary("wan-006", "success", 1, [attempt(1, ["n"], "success", 2.0)], 1)
        self.put("one", value)
        self.put("two", value)
        with self.assertRaisesRegex(wan_report.ReportError, "duplicate summary"):
            wan_report.collect(self.root)

    def test_rejects_non_wan_summary(self):
        self.put("case", summary("aq-001", "success", 1, [], 1))
        with self.assertRaisesRegex(wan_report.ReportError, "invalid WAN case ID"):
            wan_report.collect(self.root)


if __name__ == "__main__":
    unittest.main()
