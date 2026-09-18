#!/usr/bin/env python3
"""Prepare pinned serial Rodinia k-means with generated numeric inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVISION = "31d0ebf5adaf3aaa6c770cc5319a62275d8c1881"
BASE = f"https://raw.githubusercontent.com/yuhc/gpu-rodinia/{REVISION}"
PREFIX = "openmp/kmeans/kmeans_serial"
FILES = {
    "kmeans_clustering.c": (f"{PREFIX}/kmeans_clustering.c", "d17aea23962201a350e41e53db6ea0798a4c1264ef43588b3bdf8a14a08a0ee7"),
    "kmeans.h": (f"{PREFIX}/kmeans.h", "438f4a458b60f4f401e3ccd4b86964a7eae24de0a7cd09a3ec37b6866e430eed"),
    "LICENSE": ("LICENSE", "440539e50c8d134f4587a8a1c2b9434b695a626b6bd35c13356946f17ebf4a1a"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "build/evaluation-rodinia-kmeans")
    parser.add_argument("--source-dir", type=Path, help="directory containing the three pinned upstream files")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace.exists():
        parser.error(f"destination already exists: {workspace}")
    if not (ROOT / "build/libperfmark.so").is_file():
        parser.error("build Dr. Perf first with ./build.sh")
    fetched = {}
    for name, (relative, expected) in FILES.items():
        if args.source_dir:
            data = (args.source_dir / name).read_bytes()
        else:
            with urllib.request.urlopen(f"{BASE}/{relative}", timeout=30) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != expected:
            parser.error(f"upstream SHA-256 mismatch: {name}")
        fetched[name] = data
    (workspace / "rodinia").mkdir(parents=True)
    (workspace / "upstream").mkdir()
    for name, data in fetched.items():
        (workspace / "upstream" / name).write_bytes(data)
        (workspace / "rodinia" / name).write_bytes(data)
    for name in ("driver.c", "build.sh"):
        shutil.copyfile(HERE / name, workspace / name)
    (workspace / "build.sh").chmod(0o755)
    (workspace / ".drperf-workload.json").write_text(json.dumps({
        "version": 1, "instrumentation": {"driver.c": {"kind": "text-block",
            "start": "/* EVALUATION_STATES_BEGIN */", "end": "/* EVALUATION_STATES_END */"}},
        "build": ["./build.sh"], "build_outputs": ["program", "kmeans.o"]}, indent=2) + "\n")
    (workspace / "perfmark").mkdir()
    shutil.copyfile(ROOT / "perfmark/perfmark.h", workspace / "perfmark/perfmark.h")
    shutil.copyfile(ROOT / "build/libperfmark.so", workspace / "libperfmark.so")
    provenance = {
        "repository": "https://github.com/yuhc/gpu-rodinia", "revision": REVISION,
        "source_files": {name: {"url": f"{BASE}/{path}", "sha256": digest}
                         for name, (path, digest) in FILES.items()},
        "adaptations": ["Upstream serial clustering source is unchanged.",
                        "New driver generates numeric points and varies shapes in memory.",
                        "Region wraps the complete kmeans_clustering call through convergence.",
                        "Generation, result checks, printing, and returned-array cleanup are outside."],
        "compiler": subprocess.check_output(["cc", "--version"], text=True).splitlines()[0],
    }
    (workspace / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    (workspace / "README.md").write_text(
        "# Rodinia serial k-means\n\n"
        "Build: `./build.sh`. Correctness check: `./program --self-test`.\n"
        "Workload: `./program --shapes 24 --shape-seed 17 --data-seed 7`.\n\n"
        "The cluster region wraps the complete kmeans_clustering call in driver.c.\n"
        "Its implementation in rodinia/kmeans_clustering.c is unchanged from the\n"
        "pinned Rodinia serial source. Upstream files, license and provenance are included.\n"
        "The driver creates fresh numeric points in memory for each call. No dataset\n"
        "files are read. Each shape is exercised with three coordinate distributions.\n"
        "The first nclusters input points are used by upstream as initial centers.\n"
        "threshold is fixed at zero: stop when assignments no longer change.\n"
        "Generation, output validation, printing and caller cleanup are outside the region.\n")
    subprocess.run(["./build.sh"], cwd=workspace, check=True)
    subprocess.run(["./program", "--self-test"], cwd=workspace, check=True)
    print(f"Workspace ready: {workspace}")


if __name__ == "__main__":
    main()
