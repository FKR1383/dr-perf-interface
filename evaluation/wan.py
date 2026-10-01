#!/usr/bin/env python3
"""Read-only discovery and leak-free staging for annotated WAN benchmarks."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
WAN_ROOT = REPO_ROOT / "bench_anontated" / "wan"
CASE_ID_RE = re.compile(r"^wan-[0-9]{3}$")


class WanStageError(RuntimeError):
    """Raised when an annotated WAN case cannot be staged safely."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise WanStageError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WanStageError(f"expected a JSON object in {path}")
    return value


def _relative_path(value: Any, *, field: str) -> Path:
    if not isinstance(value, str):
        raise WanStageError(f"{field} must be a relative path string")
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise WanStageError(f"unsafe {field}: {value!r}")
    return path


def _case(case_id: str, wan_root: Path) -> tuple[Path, dict[str, Any]]:
    if not isinstance(case_id, str) or CASE_ID_RE.fullmatch(case_id) is None:
        raise WanStageError(f"invalid WAN case ID: {case_id!r}")
    root = wan_root.resolve()
    case_dir = (root / case_id).resolve()
    if not case_dir.is_relative_to(root) or not case_dir.is_dir():
        raise WanStageError(f"unknown WAN case: {case_id}")
    manifest = _read_json(case_dir / "case.json")
    if manifest.get("id") != case_id:
        raise WanStageError(f"case ID mismatch in {case_dir / 'case.json'}")
    return case_dir, manifest


def _regular_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WanStageError(f"symlinks are not allowed in a WAN case: {path}")
        if path.is_file():
            yield path


def tree_hashes(root: Path) -> dict[str, str]:
    """Return content hashes for every regular file below *root*."""
    result: dict[str, str] = {}
    for path in _regular_files(root):
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def list_wan_cases(wan_root: Path = WAN_ROOT) -> list[str]:
    """List valid annotated WAN case IDs without modifying the source tree."""
    root = wan_root.resolve()
    if not root.is_dir():
        raise WanStageError(f"WAN root does not exist: {root}")
    result: list[str] = []
    for manifest_path in sorted(root.glob("wan-*/case.json")):
        case_id = manifest_path.parent.name
        if CASE_ID_RE.fullmatch(case_id) is None:
            continue
        manifest = _read_json(manifest_path)
        if manifest.get("id") != case_id:
            raise WanStageError(f"case ID mismatch in {manifest_path}")
        result.append(case_id)
    return result


def _byte_offset(lines: list[bytes], line: int, column: int) -> int:
    # CPython AST columns are UTF-8 byte offsets, so source must stay as bytes.
    if line < 1 or line > len(lines):
        raise WanStageError("marker has an invalid source line")
    return sum(map(len, lines[: line - 1])) + column


def _region_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == "perfmark" and node.func.attr == "region":
                calls.append(node)
    return calls


def _target_marker(tree: ast.AST, case_id: str) -> ast.Call:
    calls = _region_calls(tree)
    if len(calls) != 1:
        raise WanStageError(f"expected exactly one perfmark.region call, found {len(calls)}")
    call = calls[0]
    if len(call.args) != 1:
        raise WanStageError("marker must have exactly one positional region-name argument")
    name = call.args[0]
    if not isinstance(name, ast.Constant) or name.value != case_id:
        raise WanStageError(f"marker must use the literal region name {case_id!r}")
    if any(keyword.arg is None for keyword in call.keywords):
        raise WanStageError("marker must not use ** keyword expansion")

    owners = []
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                if item.context_expr is call:
                    owners.append(node)
    if len(owners) != 1 or len(owners[0].items) != 1:
        raise WanStageError("marker must be the sole context manager in one with statement")
    return call


def strip_marker_keywords(source: bytes, case_id: str) -> bytes:
    """Remove only a case marker's PCV keywords, preserving its region body."""
    try:
        original = ast.parse(source)
    except SyntaxError as exc:
        raise WanStageError(f"cannot parse annotated source: {exc}") from exc
    call = _target_marker(original, case_id)
    lines = source.splitlines(keepends=True)
    start = _byte_offset(lines, call.lineno, call.col_offset)
    argument_end = _byte_offset(lines, call.args[0].end_lineno, call.args[0].end_col_offset)
    end = _byte_offset(lines, call.end_lineno, call.end_col_offset)
    stripped = source[:start] + source[start:argument_end] + b")" + source[end:]

    try:
        parsed = ast.parse(stripped)
    except SyntaxError as exc:
        raise WanStageError(f"stripped source is invalid: {exc}") from exc
    empty = _target_marker(parsed, case_id)
    if empty.keywords:
        raise WanStageError("failed to remove all marker PCVs")

    expected = copy.deepcopy(original)
    _target_marker(expected, case_id).keywords = []
    if ast.dump(expected, include_attributes=False) != ast.dump(parsed, include_attributes=False):
        raise WanStageError("stripping PCVs changed source structure outside the marker")
    return stripped


def _declared_test_paths(case_dir: Path, manifest: dict[str, Any]) -> list[Path]:
    tests = manifest.get("tests")
    if not isinstance(tests, dict) or not isinstance(tests.get("files"), list):
        raise WanStageError("case manifest has no declared tests.files list")
    result: list[Path] = []
    seen: set[Path] = set()
    for value in tests["files"]:
        relative = _relative_path(value, field="tests.files entry")
        if relative.parts[0] != "tests":
            raise WanStageError(f"declared test is outside tests/: {relative}")
        if relative in seen:
            raise WanStageError(f"duplicate declared test: {relative}")
        seen.add(relative)
        source = case_dir / relative
        if source.is_symlink() or not source.is_file():
            raise WanStageError(f"missing declared test: {source}")
        result.append(relative)
    return result


def _static_iterable_count(node: ast.AST) -> tuple[int, str] | None:
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            return None
        return len(value), type(node).__name__.lower()
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "range"
        and not node.keywords
        and 1 <= len(node.args) <= 3
    ):
        try:
            args = [ast.literal_eval(argument) for argument in node.args]
            if not all(isinstance(value, int) for value in args):
                return None
            count = len(range(*args))
        except (ValueError, TypeError):
            return None
        return count, "range"
    return None


def audit_workload(case_id: str, wan_root: Path = WAN_ROOT) -> dict[str, Any]:
    """Report declared workload assets and statically enumerable input groups.

    The counts describe literal loop iterables visible in declared Python test
    assets. They are an audit aid, not dynamic branch- or marker-call coverage.
    """
    case_dir, manifest = _case(case_id, wan_root)
    tests = _declared_test_paths(case_dir, manifest)
    groups: list[dict[str, Any]] = []
    for relative in tests:
        if relative.suffix != ".py":
            continue
        path = case_dir / relative
        try:
            tree = ast.parse(path.read_bytes())
        except SyntaxError as exc:
            raise WanStageError(f"cannot parse declared test {path}: {exc}") from exc
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.comprehension)):
                continue
            item = _static_iterable_count(node.iter)
            if item is None:
                continue
            count, kind = item
            groups.append({
                "file": relative.as_posix(),
                "line": node.lineno,
                "count": count,
                "kind": kind,
            })
    groups.sort(key=lambda item: (item["file"], item["line"]))
    test_case = Path("tests/test_case.py")
    return {
        "case_id": case_id,
        "test_case_declared": test_case in tests,
        "test_case_present": (case_dir / test_case).is_file(),
        "declared_test_files": [path.as_posix() for path in tests],
        "static_configuration_groups": groups,
        "static_configuration_group_count": len(groups),
        "static_configuration_count": sum(item["count"] for item in groups),
    }


def _copy_file(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise WanStageError(f"cannot stage non-regular file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def stage_wan_case(
    case_id: str,
    destination: Path,
    wan_root: Path = WAN_ROOT,
) -> dict[str, Any]:
    """Create a leak-free evaluation copy of one annotated WAN case."""
    case_dir, manifest = _case(case_id, wan_root)
    destination = destination.resolve()
    source_root = wan_root.resolve()
    if destination.is_relative_to(source_root):
        raise WanStageError("staging destination must be outside bench_anontated/wan")
    if destination.exists():
        raise WanStageError(f"staging destination already exists: {destination}")

    source_relative = _relative_path(manifest.get("source", {}).get("path"), field="source.path")
    source = case_dir / source_relative
    if source.is_symlink() or not source.is_file():
        raise WanStageError(f"missing declared source: {source}")
    tests = _declared_test_paths(case_dir, manifest)
    before = tree_hashes(case_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f".{case_id}-stage-", dir=destination.parent) as temporary:
        staged = Path(temporary) / case_id
        staged.mkdir()
        target_source = staged / source_relative
        target_source.parent.mkdir(parents=True, exist_ok=True)
        target_source.write_bytes(strip_marker_keywords(source.read_bytes(), case_id))
        for relative in tests:
            _copy_file(case_dir / relative, staged / relative)
        licenses = case_dir / "LICENSES"
        if licenses.exists():
            if licenses.is_symlink() or not licenses.is_dir():
                raise WanStageError(f"invalid LICENSES directory: {licenses}")
            for license_file in _regular_files(licenses):
                _copy_file(license_file, staged / "LICENSES" / license_file.relative_to(licenses))

        public_manifest = copy.deepcopy(manifest)
        marker = public_manifest.get("marker")
        if not isinstance(marker, dict):
            raise WanStageError("case manifest has no marker object")
        marker["pcvs"] = []
        (staged / "case.json").write_text(json.dumps(public_manifest, indent=2) + "\n")
        (staged / "TASK.md").write_text(
            f"# {case_id}\n\n"
            "Find cheap state expressions available at entry to the existing "
            "`perfmark.region` that explain its instruction count. Derived features, "
            "products, powers, comparisons, conditional expressions, and relevant "
            "runtime or library state are allowed. Preserve the marked region, program "
            "behavior, and workload.\n"
        )

        after = tree_hashes(case_dir)
        if after != before:
            raise WanStageError("annotated WAN case changed while it was being staged")
        os.replace(staged, destination)

    return {
        "case_id": case_id,
        "destination": str(destination),
        "source_path": source_relative.as_posix(),
        "original_tree_hashes": before,
        "workload_audit": audit_workload(case_id, wan_root),
    }

