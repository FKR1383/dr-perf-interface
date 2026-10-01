#!/usr/bin/env python3
"""vLLM-specific facade over the generic suite report renderer."""

from __future__ import annotations

import json
from pathlib import Path
import re

import wan_report as _report


_report.CASE_RE = re.compile(r"^vllm-(\d+)$")
ReportError = _report.ReportError
collect = _report.collect
flat_rows = _report.flat_rows
render_csv = _report.render_csv
render_markdown = _report.render_markdown


def write_reports(suite_root: Path, output_dir: Path):
    report = collect(suite_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "vllm-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "vllm-report.csv").write_text(render_csv(report))
    (output_dir / "vllm-report.md").write_text(render_markdown(report))
    return report

