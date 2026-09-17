#!/usr/bin/env python3
"""Build the isolated partial_sync CUDA CPU-exclusion client from a pinned GX tree."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


BASE_HASHES = {
    "client.c": "078f8e93af69518899cf131fa096e1f140cc8a3a0815e8325feb2342cbe60cb0",
    "CMakeLists.txt": "5554fbc8a223f4940753e1447e36ea9bee3285c7915c03d7dfda495febb519d3",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gx-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path,
                        help="new, empty isolated source/build directory")
    parser.add_argument("--dynamorio-dir", type=Path,
                        help="defaults to GX/build/gxvm-install/stage/dynamorio/cmake")
    args = parser.parse_args()
    gx = args.gx_root.resolve()
    output = args.output.resolve()
    dr = (args.dynamorio_dir or gx / "build/gxvm-install/stage/dynamorio/cmake").resolve()
    base = gx / "tools/gxvm/experimental/timeline"
    if output.exists() and any(output.iterdir()):
        parser.error(f"output must be empty: {output}")
    for name, expected in BASE_HASHES.items():
        actual = sha(base / name)
        if actual != expected:
            parser.error(f"GX {name} hash differs from pinned patch base: {actual}")
    if not (dr / "DynamoRIOConfig.cmake").is_file():
        parser.error(f"missing DynamoRIO CMake config: {dr}")
    target = output / "tools/gxvm/experimental/timeline"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("client.c", "sampling.c", "sampling.h", "CMakeLists.txt"):
        shutil.copy2(base / name, target / name)
    for name in ("dr_scheduler", "extension"):
        (output / "tools/gxvm" / name).symlink_to(gx / "tools/gxvm" / name,
                                                    target_is_directory=True)
    patch = Path(__file__).with_name("gxvm_timeline_cuda_cpu_exclusion.patch")
    with patch.open("rb") as stream:
        subprocess.run(["patch", "--batch", "-p1", "-d", str(output)],
                       stdin=stream, check=True)
    build = output / "build"
    subprocess.run(["cmake", "-S", str(target), "-B", str(build),
                    f"-DDynamoRIO_DIR={dr}"], check=True)
    subprocess.run(["cmake", "--build", str(build), "--target", "gxvm_timeline_client",
                    "-j8"], check=True)
    library = build / "libgxvm_timeline_client.so"
    if not library.is_file():
        raise RuntimeError("timeline client build did not produce a library")
    manifest = {
        "gx_root": str(gx), "dynamorio_dir": str(dr), "patch_sha256": sha(patch),
        "base_sha256": BASE_HASHES,
        "linked_dependency_sha256": {
            str(relative): sha(gx / relative) for relative in (
                Path("tools/gxvm/dr_scheduler/native_ipc_replay.c"),
                Path("tools/gxvm/dr_scheduler/native_ipc_replay.h"),
                Path("tools/gxvm/extension/gpu/native_execution.c"),
                Path("tools/gxvm/extension/gpu/native_execution.h"))},
        "library": str(library), "library_sha256": sha(library),
    }
    (output / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(library)


if __name__ == "__main__":
    main()
