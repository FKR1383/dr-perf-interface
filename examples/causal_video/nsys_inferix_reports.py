"""Summarize a measured Inferix Nsight SQLite capture without loading a model.

Nsight starts capture only at the measured NVTX range, so all activity in the
database belongs to that range. CUDA API sums count overlapping host calls and
must not be interpreted as end-to-end wall time.
"""

import argparse
import json
from pathlib import Path
import sqlite3


def summarize(path: Path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    result = {}
    for category, table, bytes_column in (
        ("cuda_api", "CUPTI_ACTIVITY_KIND_RUNTIME", None),
        ("gpu_kernel", "CUPTI_ACTIVITY_KIND_KERNEL", None),
        ("gpu_memcpy", "CUPTI_ACTIVITY_KIND_MEMCPY", "bytes"),
        ("gpu_memset", "CUPTI_ACTIVITY_KIND_MEMSET", "bytes"),
    ):
        if table not in tables:
            result[category] = {"count": 0, "duration_ms_sum": 0.0}
            continue
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if not {"start", "end"}.issubset(columns):
            raise ValueError(f"{table} has no start/end columns: {sorted(columns)}")
        fields = "COUNT(*), SUM(end-start)"
        if bytes_column in columns:
            fields += f", SUM({bytes_column})"
        row = db.execute(f"SELECT {fields} FROM {table}").fetchone()
        result[category] = {"count": row[0], "duration_ms_sum": (row[1] or 0) / 1e6}
        if bytes_column in columns:
            result[category]["bytes_sum"] = row[2] or 0
        if category == "gpu_memcpy" and "copyKind" in columns:
            result[category]["by_copy_kind"] = [
                {"copy_kind": kind, "count": count, "duration_ms_sum": (ns or 0) / 1e6,
                 "bytes_sum": size or 0}
                for kind, count, ns, size in db.execute(
                    f"SELECT copyKind, COUNT(*), SUM(end-start), SUM({bytes_column}) "
                    f"FROM {table} GROUP BY copyKind ORDER BY copyKind")
            ]
    db.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sqlite", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize(args.sqlite)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
