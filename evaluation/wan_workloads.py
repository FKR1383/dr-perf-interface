#!/usr/bin/env python3
"""Expand the small collected WAN fixtures in an isolated staged case.

The annotated benchmark tree is reference material and must remain immutable.
This module therefore accepts a staged case root, rewrites only its
``tests/helper.py``, and returns a JSON-serializable audit record.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANNOTATED_ROOT = Path(__file__).resolve().parents[1] / "bench_anontated"
MINIMUM_CONFIGURATIONS = 6


class WanWorkloadError(RuntimeError):
    """Raised when a staged WAN workload cannot be expanded safely."""


@dataclass(frozen=True)
class MatrixExpansion:
    name: str
    variables: tuple[str, ...]
    original: str
    expanded: str
    matrix: tuple[Any, ...]
    notes: str
    extra_audit: tuple[tuple[str, Any], ...] = ()
    is_matrix: bool = True


# Each matrix varies one or more axes independently instead of scaling every
# dimension in lockstep.  Sizes remain deliberately small for offline CPU use.
EXPANSIONS: tuple[MatrixExpansion, ...] = (
    MatrixExpansion(
        "image",
        ("batch", "height", "width"),
        "for batch, height, width in ((1, 6, 8), (2, 8, 8), (1, 10, 12)):",
        "for batch, height, width in ((1, 6, 8), (2, 6, 8), (1, 8, 8), (1, 6, 12), (2, 10, 8), (1, 10, 12)):",
        ((1, 6, 8), (2, 6, 8), (1, 8, 8), (1, 6, 12), (2, 10, 8), (1, 10, 12)),
        "Separates batch, height, and width while retaining the original endpoints.",
    ),
    MatrixExpansion(
        "gaussian_parameters",
        ("batch", "frames", "side"),
        "for batch, frames, side in ((1, 1, 2), (2, 2, 3), (1, 3, 4)):",
        "for batch, frames, side in ((1, 1, 2), (2, 1, 2), (1, 2, 2), (1, 1, 3), (2, 2, 3), (1, 3, 4)):",
        ((1, 1, 2), (2, 1, 2), (1, 2, 2), (1, 1, 3), (2, 2, 3), (1, 3, 4)),
        "Separates batch, temporal extent, and spatial extent.",
    ),
    MatrixExpansion(
        "blend_extent",
        ("extent",),
        "for extent in (1, 2, 3):",
        "for extent in (1, 2, 3, 4, 5, 6):",
        (1, 2, 3, 4, 5, 6),
        "Exercises six positive loop lengths that retain unblended endpoints on a bounded 9x9 plane.",
        (("fixed_tensor_shape", (1, 2, 2, 9, 9)),),
    ),
    MatrixExpansion(
        "blend_tensor",
        ("batch", "channels", "frames", "height", "width"),
        "a = torch.zeros(1, 2, 2, 5, 5); b = torch.ones_like(a)",
        "a = torch.zeros(1, 2, 2, 9, 9); b = torch.ones_like(a)",
        ((1, 2, 2, 9, 9),),
        "Supporting shape for the six distinct blend extents.",
        is_matrix=False,
    ),
    MatrixExpansion(
        "cache_offset",
        ("offset",),
        "for offset in (0, 1, 3):",
        "for offset in (0, 1, 2, 3, 5, 8):",
        (0, 1, 2, 3, 5, 8),
        "Covers zero plus five bounded nonzero cache-index seeds.",
    ),
    MatrixExpansion(
        "vae_video",
        ("frames", "side"),
        "for frames, side in ((1, 16), (5, 32), (9, 48)):",
        "for frames, side in ((1, 16), (5, 16), (1, 32), (9, 16), (5, 32), (9, 48)):",
        ((1, 16), (5, 16), (1, 32), (9, 16), (5, 32), (9, 48)),
        "Separates temporal and spatial VAE scaling and retains a bounded hard case.",
    ),
    MatrixExpansion(
        "transformer",
        ("frames", "side", "text_length"),
        "for frames, side, text_length in ((1, 6, 4), (2, 8, 6), (3, 8, 9)):",
        "for frames, side, text_length in ((1, 6, 4), (2, 6, 9), (1, 8, 6), (3, 6, 6), (2, 8, 4), (3, 8, 9)):",
        ((1, 6, 4), (2, 6, 9), (1, 8, 6), (3, 6, 6), (2, 8, 4), (3, 8, 9)),
        "De-correlates patch-grid tokens and text context length.",
    ),
    MatrixExpansion(
        "prompt_encoding",
        ("prompts", "max_length"),
        'for prompts, max_length in ((["red kite"], 8), (["small red kite", "blue boat"], 12), (["one calm lake"], 16)):',
        'for prompts, max_length in ((["red kite"], 8), (["small red kite"], 8), (["blue boat", "red kite"], 8), (["one calm lake"], 12), (["bright red kite", "blue boat"], 16), (["one calm lake at dawn"], 16)):',
        (
            (("red kite",), 8),
            (("small red kite",), 8),
            (("blue boat", "red kite"), 8),
            (("one calm lake",), 12),
            (("bright red kite", "blue boat"), 16),
            (("one calm lake at dawn",), 16),
        ),
        "Separates prompt batch, content length, and padded sequence length.",
    ),
    MatrixExpansion(
        "pipeline",
        ("text_length", "steps", "seed"),
        "for text_length, steps, seed in ((4, 1, 3), (8, 2, 5), (12, 3, 7)):",
        "for text_length, steps, seed in ((4, 1, 3), (8, 1, 5), (4, 2, 7), (12, 2, 11), (8, 3, 13), (12, 4, 17)):",
        ((4, 1, 3), (8, 1, 5), (4, 2, 7), (12, 2, 11), (8, 3, 13), (12, 4, 17)),
        "Separates context length from denoising steps with deterministic seeds.",
    ),
    MatrixExpansion(
        "latent_preparation",
        ("batch", "frames", "side"),
        "for batch, frames, side in ((1, 1, 16), (2, 5, 32), (1, 9, 48)):",
        "for batch, frames, side in ((1, 1, 16), (2, 1, 16), (1, 5, 16), (1, 1, 32), (2, 5, 32), (1, 9, 48)):",
        ((1, 1, 16), (2, 1, 16), (1, 5, 16), (1, 1, 32), (2, 5, 32), (1, 9, 48)),
        "Separates batch, temporal extent, and spatial extent.",
    ),
    MatrixExpansion(
        "scheduler_steps",
        ("steps",),
        "for steps in (2, 4, 6):",
        "for steps in (1, 2, 3, 4, 6, 8):",
        (1, 2, 3, 4, 6, 8),
        "Adds easy, intermediate, and hard bounded schedule lengths.",
    ),
    MatrixExpansion(
        "video",
        ("batch", "frames", "side"),
        "for batch, frames, side in ((1, 1, 6), (2, 3, 8), (1, 5, 10)):",
        "for batch, frames, side in ((1, 1, 6), (2, 1, 6), (1, 3, 6), (1, 1, 8), (2, 3, 8), (1, 5, 10)):",
        ((1, 1, 6), (2, 1, 6), (1, 3, 6), (1, 1, 8), (2, 3, 8), (1, 5, 10)),
        "Separates batch, frame count, and spatial size.",
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _assertions(source: str, filename: str) -> list[str]:
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise WanWorkloadError(f"invalid Python in {filename}: {exc}") from exc
    return [ast.dump(node) for node in ast.walk(tree) if isinstance(node, ast.Assert)]


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _matrix_audit(expansion: MatrixExpansion, status: str) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": expansion.name,
        "variables": list(expansion.variables),
        "count": len(expansion.matrix),
        "matrix": [list(row) if isinstance(row, tuple) else row for row in expansion.matrix],
        "notes": expansion.notes,
        "status": status,
    }
    item.update(expansion.extra_audit)
    return item


def expand_staged_wan_workload(case_root: str | Path) -> dict[str, Any]:
    """Expand a staged WAN helper and return a JSON-serializable audit.

    ``case_root`` must contain ``tests/test_case.py`` and ``tests/helper.py``.
    The operation is idempotent and atomic.  Partially expanded helpers are
    accepted, while missing or duplicate known matrices are rejected.
    """

    root = Path(case_root).resolve()
    annotated = ANNOTATED_ROOT.resolve()
    if _inside(root, annotated):
        raise WanWorkloadError("refusing to modify the immutable bench_anontated tree")

    tests = root / "tests"
    launcher = tests / "test_case.py"
    helper = tests / "helper.py"
    for path, label in ((launcher, "tests/test_case.py"), (helper, "tests/helper.py")):
        if path.is_symlink():
            raise WanWorkloadError(f"{label} must not be a symlink")
        if not path.is_file():
            raise WanWorkloadError(f"missing required staged file: {label}")
        if not _inside(path.resolve(), root):
            raise WanWorkloadError(f"{label} resolves outside the staged case")

    original_bytes = helper.read_bytes()
    try:
        original = original_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WanWorkloadError("tests/helper.py is not UTF-8") from exc
    original_assertions = _assertions(original, str(helper))

    expanded = original
    statuses: dict[str, str] = {}
    for item in EXPANSIONS:
        old_count = expanded.count(item.original)
        new_count = expanded.count(item.expanded)
        if old_count == 1 and new_count == 0:
            expanded = expanded.replace(item.original, item.expanded, 1)
            statuses[item.name] = "expanded"
        elif old_count == 0 and new_count == 1:
            statuses[item.name] = "already-expanded"
        else:
            raise WanWorkloadError(
                f"cannot identify {item.name} matrix exactly once "
                f"(original={old_count}, expanded={new_count})"
            )

    expanded_assertions = _assertions(expanded, str(helper))
    if expanded_assertions != original_assertions:
        raise WanWorkloadError("workload expansion changed correctness assertions")
    for item in EXPANSIONS:
        if item.is_matrix and len(item.matrix) < MINIMUM_CONFIGURATIONS:
            raise WanWorkloadError(f"{item.name} has fewer than six configurations")

    expanded_bytes = expanded.encode("utf-8")
    changed = expanded_bytes != original_bytes
    if changed:
        temporary = helper.with_name(helper.name + ".wan-workload.tmp")
        temporary.write_bytes(expanded_bytes)
        temporary.replace(helper)

    return {
        "schema_version": 1,
        "case_root": str(root),
        "launcher": "tests/test_case.py",
        "launcher_exists": True,
        "helper": "tests/helper.py",
        "changed": changed,
        "minimum_configurations": MINIMUM_CONFIGURATIONS,
        "assertion_count": len(original_assertions),
        "assertions_preserved": True,
        "helper_sha256_before": _sha256(original_bytes),
        "helper_sha256_after": _sha256(expanded_bytes),
        "families": [_matrix_audit(item, statuses[item.name]) for item in EXPANSIONS if item.is_matrix],
        "supporting_inputs": [_matrix_audit(item, statuses[item.name]) for item in EXPANSIONS if not item.is_matrix],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_root", type=Path, help="isolated staged WAN case root")
    args = parser.parse_args(argv)
    try:
        audit = expand_staged_wan_workload(args.case_root)
    except WanWorkloadError as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
