import ast
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import wan_workloads


WAN_ROOT = Path(__file__).resolve().parents[1] / "bench_anontated" / "wan"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assertions(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    return [ast.dump(node) for node in ast.walk(tree) if isinstance(node, ast.Assert)]


class WanWorkloadExpansionTests(unittest.TestCase):
    def stage(self, case_id):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / case_id
        tests = root / "tests"
        tests.mkdir(parents=True)
        source = WAN_ROOT / case_id / "tests"
        shutil.copy2(source / "helper.py", tests / "helper.py")
        shutil.copy2(source / "test_case.py", tests / "test_case.py")
        return temporary, root

    def test_representative_helpers_expand_without_touching_sources(self):
        for case_id in ("wan-001", "wan-009", "wan-025", "wan-037", "wan-040"):
            with self.subTest(case_id=case_id):
                source_helper = WAN_ROOT / case_id / "tests" / "helper.py"
                source_before = digest(source_helper)
                temporary, staged = self.stage(case_id)
                self.addCleanup(temporary.cleanup)
                staged_helper = staged / "tests" / "helper.py"
                before_assertions = assertions(staged_helper)

                audit = wan_workloads.expand_staged_wan_workload(staged)

                self.assertTrue(audit["changed"])
                self.assertTrue(audit["launcher_exists"])
                self.assertTrue(audit["assertions_preserved"])
                self.assertEqual(audit["assertion_count"], len(before_assertions))
                self.assertEqual(assertions(staged_helper), before_assertions)
                self.assertEqual(digest(source_helper), source_before)
                self.assertNotEqual(digest(staged_helper), source_before)
                self.assertGreaterEqual(len(audit["families"]), 10)
                self.assertTrue(all(row["count"] >= 6 for row in audit["families"]))
                json.dumps(audit)

    def test_all_known_matrices_are_expanded_and_audit_is_idempotent(self):
        temporary, staged = self.stage("wan-025")
        self.addCleanup(temporary.cleanup)
        first = wan_workloads.expand_staged_wan_workload(staged)
        helper = staged / "tests" / "helper.py"
        first_digest = digest(helper)

        for expansion in wan_workloads.EXPANSIONS:
            text = helper.read_text()
            self.assertNotIn(expansion.original, text)
            self.assertEqual(text.count(expansion.expanded), 1)

        second = wan_workloads.expand_staged_wan_workload(staged)
        self.assertFalse(second["changed"])
        self.assertEqual(digest(helper), first_digest)
        self.assertTrue(all(row["status"] == "already-expanded" for row in second["families"]))
        self.assertEqual(
            [row["matrix"] for row in first["families"]],
            [row["matrix"] for row in second["families"]],
        )

    def test_missing_test_case_is_rejected_before_helper_change(self):
        temporary, staged = self.stage("wan-001")
        self.addCleanup(temporary.cleanup)
        helper = staged / "tests" / "helper.py"
        before = digest(helper)
        (staged / "tests" / "test_case.py").unlink()

        with self.assertRaisesRegex(wan_workloads.WanWorkloadError, "test_case.py"):
            wan_workloads.expand_staged_wan_workload(staged)
        self.assertEqual(digest(helper), before)

    def test_unrecognized_matrix_is_rejected_atomically(self):
        temporary, staged = self.stage("wan-037")
        self.addCleanup(temporary.cleanup)
        helper = staged / "tests" / "helper.py"
        text = helper.read_text().replace("for steps in (2, 4, 6):", "for steps in (2, 5, 6):")
        helper.write_text(text)
        before = digest(helper)

        with self.assertRaisesRegex(wan_workloads.WanWorkloadError, "scheduler_steps"):
            wan_workloads.expand_staged_wan_workload(staged)
        self.assertEqual(digest(helper), before)

    def test_annotated_tree_is_immutable(self):
        case = WAN_ROOT / "wan-001"
        before = digest(case / "tests" / "helper.py")
        with self.assertRaisesRegex(wan_workloads.WanWorkloadError, "immutable"):
            wan_workloads.expand_staged_wan_workload(case)
        self.assertEqual(digest(case / "tests" / "helper.py"), before)


if __name__ == "__main__":
    unittest.main()
