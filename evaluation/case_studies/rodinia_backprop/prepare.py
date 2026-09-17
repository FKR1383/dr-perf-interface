#!/usr/bin/env python3
"""Prepare a pinned Rodinia Backprop CPU workload with generated numeric data."""
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
FILES = {
    "backprop.c": ("openmp/backprop/backprop.c", "061de3aae718474769282067e8842f469539d14dac581b1cead8de8fee73b880"),
    "backprop.h": ("openmp/backprop/backprop.h", "1e00611c60453cacb26e05c023a99636e0afc53ffbcfc483548f7b10997c8651"),
    "LICENSE": ("LICENSE", "440539e50c8d134f4587a8a1c2b9434b695a626b6bd35c13356946f17ebf4a1a"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "build/evaluation-rodinia-backprop")
    parser.add_argument("--source-dir", type=Path, help="directory with the three pinned upstream files")
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
        if name == "backprop.c":
            assert data.count(b"#define OPEN\r\n") == 1
            data = data.replace(b"#define OPEN\r\n", b"/* Serial CPU configuration. */\r\n#undef OPEN\r\n", 1)
        (workspace / "rodinia" / name).write_bytes(data)
    for name in ("driver.c", "build.sh"):
        shutil.copyfile(HERE / name, workspace / name)
    (workspace / "build.sh").chmod(0o755)
    (workspace / "perfmark").mkdir()
    shutil.copyfile(ROOT / "perfmark/perfmark.h", workspace / "perfmark/perfmark.h")
    shutil.copyfile(ROOT / "build/libperfmark.so", workspace / "libperfmark.so")
    record = {"repository": "https://github.com/yuhc/gpu-rodinia", "revision": REVISION,
              "source_files": {name: {"url": f"{BASE}/{p}", "sha256": digest}
                               for name, (p, digest) in FILES.items()},
              "adaptations": ["Disable OPEN to select serial CPU execution; computation loops unchanged.",
                              "Use a new driver with variable network dimensions and repeated training steps.",
                              "Generate inputs, targets and scaled initial weights in memory from a fixed seed.",
                              "Wrap training steps in perfmark; setup and checks stay outside."],
              "compiler": subprocess.check_output(["cc", "--version"], text=True).splitlines()[0]}
    (workspace / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    (workspace / "README.md").write_text(
        "# Rodinia Backprop CPU workload\n\n"
        "Build: `./build.sh`. Correctness check: `./program --self-test`.\n"
        "Workload: `./program --cases 96 --shape-seed 17 --data-seed 7`.\n\n"
        "The train region in driver.c covers calls to Rodinia's bpnn_train, including\n"
        "forward propagation, output and hidden error computation, and weight updates.\n"
        "Inputs, targets and initial weights are generated in memory. No dataset or\n"
        "database is read. Shape and data seeds control separate random generators.\n"
        "Allocation, initialization, output checks and printing are outside the region.\n"
        "Each case uses a fresh network. This is a serial CPU adaptation of the Rodinia\n"
        "3.1 source; upstream source, license and provenance are included.\n")
    subprocess.run(["./build.sh"], cwd=workspace, check=True)
    subprocess.run(["./program", "--self-test"], cwd=workspace, check=True)
    print(f"Workspace ready: {workspace}")


if __name__ == "__main__":
    main()
