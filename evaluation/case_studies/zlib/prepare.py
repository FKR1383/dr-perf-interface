#!/usr/bin/env python3
"""Prepare the pinned zlib case and a separate validation workload."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
URL = "https://zlib.net/fossils/zlib-1.3.1.tar.gz"
SHA256 = "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"
LEVELS = [1, 3, 4, 6]
DISCOVERY_SIZES = [1024, 4096, 16384, 32768, 49152, 65536]
VALIDATION_SIZES = [2048, 8192, 24576, 40960, 57344, 73728]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def random_bytes(length, seed):
    # Counter-mode SHA-256 gives deterministic bytes across Python versions.
    return b"".join(hashlib.sha256(f"{seed}:{i}".encode()).digest()
                    for i in range((length + 31) // 32))[:length]


def prepare_inputs(destination, source, sizes, validation=False):
    inputs = destination / "inputs"
    inputs.mkdir(parents=True)
    maximum = max(sizes)
    offset = 4096 if validation else 0
    for name, filename in (("source", "deflate.c"), ("text", "ChangeLog")):
        data = (source / filename).read_bytes()
        if len(data) < maximum + offset:
            raise ValueError(f"{filename} is too short for the selected slices")
        (inputs / f"{name}.bin").write_bytes(data[offset:offset + maximum])
    pattern = b"0123456789abcdef" if validation else b"abcd"
    (inputs / "repetitive.bin").write_bytes((pattern * (maximum // len(pattern) + 1))[:maximum])
    (inputs / "random.bin").write_bytes(random_bytes(maximum, "validation" if validation else "discovery"))
    workloads = destination / "workloads"
    workloads.mkdir()
    name = "validation" if validation else "discovery"
    manifest = workloads / f"{name}.tsv"
    manifest.write_text("# input_path bytes compression_level\n" + "".join(
        f"inputs/{kind}.bin\t{size}\t{level}\n"
        for kind in ("source", "text", "repetitive", "random")
        for size in sizes for level in LEVELS))
    return {"sizes": sizes, "levels": LEVELS, "calls": 4 * len(sizes) * len(LEVELS),
            "files": {str(p.relative_to(destination)): digest(p)
                      for p in [manifest, *sorted(inputs.glob("*"))]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT / "build/evaluation-zlib")
    parser.add_argument("--validation-dir", type=Path, default=ROOT / "build/evaluation-zlib-validation")
    parser.add_argument("--archive", type=Path, help="use an already downloaded source archive")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    validation = args.validation_dir.resolve()
    if workspace == validation or workspace in validation.parents or validation in workspace.parents:
        parser.error("workspace and validation directory must be separate")
    for path in (workspace, validation):
        if path.exists():
            parser.error(f"destination already exists: {path}")
    library = ROOT / "build/libperfmark.so"
    if not library.is_file():
        parser.error("build Dr. Perf first with ./build.sh")
    archive = args.archive or ROOT / "build/zlib-1.3.1.tar.gz"
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive.write_bytes(response.read())
    if digest(archive) != SHA256:
        parser.error("zlib archive checksum mismatch")
    source = workspace / "zlib"
    source.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts
            if not parts or parts[0] != "zlib-1.3.1" or ".." in parts:
                raise ValueError("unexpected archive path")
            target = source.joinpath(*parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as file:
                    target.write_bytes(file.read())
            else:
                raise ValueError("unsupported archive entry")
    for filename in ("driver.c", "build.sh"):
        shutil.copyfile(HERE / filename, workspace / filename)
    (workspace / "build.sh").chmod(0o755)
    (workspace / "perfmark").mkdir()
    shutil.copyfile(ROOT / "perfmark/perfmark.h", workspace / "perfmark/perfmark.h")
    shutil.copyfile(library, workspace / "libperfmark.so")
    discovery = prepare_inputs(workspace, source, DISCOVERY_SIZES)
    heldout = prepare_inputs(validation, source, VALIDATION_SIZES, validation=True)
    (workspace / "README.md").write_text(
        "# zlib compression workload\n\n"
        "Build with `./build.sh`; run with `./program workloads/discovery.tsv`.\n"
        "The `compress` region in driver.c measures calls to the bundled zlib 1.3.1.\n"
        "Loading, allocation, initialization, and round-trip verification are outside it.\n"
        "The workload manifest fixes file slices, lengths, and compression levels.\n"
        "Each input is compressed from a fresh stream and verified by decompression.\n"
        "zlib source and its license are in zlib/.\n")
    provenance = {"url": URL, "archive_sha256": SHA256, "discovery": discovery,
                  "validation": heldout, "region": "compress",
                  "driver_sha256": digest(workspace / "driver.c")}
    (validation / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    subprocess.run(["./build.sh"], cwd=workspace, check=True)
    subprocess.run(["./program", "workloads/discovery.tsv"], cwd=workspace, check=True)
    print(f"Workspace: {workspace}")
    print(f"Validation inputs: {validation}")


if __name__ == "__main__":
    main()
