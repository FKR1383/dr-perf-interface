import ast
import json
from pathlib import Path
import tempfile
import unittest

import wan


class WanInventoryTests(unittest.TestCase):
    def test_lists_all_current_wan_cases(self):
        cases = wan.list_wan_cases()
        self.assertEqual(len(cases), 41)
        self.assertEqual(cases[0], "wan-001")
        self.assertEqual(cases[-1], "wan-041")

    def test_workload_audit_finds_entrypoint_and_static_configurations(self):
        audit = wan.audit_workload("wan-001")
        self.assertTrue(audit["test_case_declared"])
        self.assertTrue(audit["test_case_present"])
        self.assertIn("tests/test_case.py", audit["declared_test_files"])
        self.assertGreater(audit["static_configuration_group_count"], 0)
        self.assertGreaterEqual(audit["static_configuration_count"], 3)
        self.assertTrue(all(item["count"] > 0 for item in audit["static_configuration_groups"]))


class MarkerStripTests(unittest.TestCase):
    def test_strips_derived_pcvs_without_changing_region_body(self):
        source = b'''import perfmark\n\ndef f(items, flag):\n    before = 1\n    with perfmark.region("wan-999", product=len(items) ** 2, branch=1 if flag else 0):\n        result = sum(items)\n        return result\n'''
        stripped = wan.strip_marker_keywords(source, "wan-999")
        self.assertIn(b'with perfmark.region("wan-999"):', stripped)
        self.assertIn(b"        result = sum(items)\n        return result\n", stripped)
        call = next(
            node
            for node in ast.walk(ast.parse(stripped))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "region"
        )
        self.assertEqual(call.keywords, [])

    def test_empty_marker_is_idempotent(self):
        source = b'import perfmark\nwith perfmark.region("wan-999"):\n    pass\n'
        self.assertEqual(wan.strip_marker_keywords(source, "wan-999"), source)

    def test_rejects_multiple_markers(self):
        source = b'''import perfmark\nwith perfmark.region("wan-999", n=1):\n    pass\nwith perfmark.region("wan-999", n=2):\n    pass\n'''
        with self.assertRaisesRegex(wan.WanStageError, "exactly one"):
            wan.strip_marker_keywords(source, "wan-999")

    def test_rejects_keyword_expansion(self):
        source = b'import perfmark\nwith perfmark.region("wan-999", **values):\n    pass\n'
        with self.assertRaisesRegex(wan.WanStageError, "expansion"):
            wan.strip_marker_keywords(source, "wan-999")


class WanStageTests(unittest.TestCase):
    def test_stages_allowlisted_assets_and_preserves_annotated_tree(self):
        case_dir = wan.WAN_ROOT / "wan-002"
        before = wan.tree_hashes(case_dir)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "staged"
            report = wan.stage_wan_case("wan-002", destination)

            self.assertEqual(wan.tree_hashes(case_dir), before)
            self.assertEqual(report["original_tree_hashes"], before)
            self.assertTrue((destination / "tests" / "test_case.py").is_file())
            self.assertTrue((destination / "TASK.md").is_file())
            self.assertTrue((destination / "LICENSES" / "LICENSE").is_file())
            self.assertFalse((destination / "result.json").exists())
            self.assertFalse((destination / "annotation.patch").exists())
            self.assertFalse((destination / "measurements").exists())

            manifest = json.loads((destination / "case.json").read_text())
            self.assertEqual(manifest["marker"]["pcvs"], [])
            source = (destination / manifest["source"]["path"]).read_bytes()
            marker = wan._target_marker(ast.parse(source), "wan-002")
            self.assertEqual(marker.keywords, [])

    def test_rejects_destination_inside_annotated_tree(self):
        destination = wan.WAN_ROOT / "wan-001" / "staged"
        with self.assertRaisesRegex(wan.WanStageError, "outside"):
            wan.stage_wan_case("wan-001", destination)


if __name__ == "__main__":
    unittest.main()
