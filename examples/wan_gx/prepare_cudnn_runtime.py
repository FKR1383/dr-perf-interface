"""Apply the experimental patch in a fresh overlay; never edit shared GX."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--gx-root', type=Path, default=Path('/home/ubuntu/GX/NEX'))
parser.add_argument('--output', type=Path, default=ROOT/'out/wan-timing/gx-cudnn-source')
args = parser.parse_args()
patches = Path(__file__).with_name('gx_patches')
manifest = json.loads((patches/'source-sha256.json').read_text())
assert not args.output.exists(), 'Use a fresh overlay; preserve ongoing experiments'
for relative, hashes in manifest.items():
    source = args.gx_root/relative
    data = source.read_bytes() if source.exists() else b''
    assert hashlib.sha256(data).hexdigest() == hashes['base_sha256'], (
        f'GX source differs from the reviewed patch base: {source}')


def overlay(source, target, split):
    target.mkdir(parents=True)
    for child in source.iterdir():
        if child.name == '.git' or child.name.startswith('bazel-') or child.name in ('build', 'out'):
            continue
        dest = target/child.name
        if child.name in split:
            if split[child.name] is None:
                shutil.copytree(child, dest)
            else:
                overlay(child, dest, split[child.name])
        else:
            dest.symlink_to(child.resolve(), target_is_directory=child.is_dir())


overlay(args.gx_root.resolve(), args.output, {'src': {'sims': {'gpu': None}, 'profile': None}})
subprocess.run(['patch', '--batch', '--forward', '-p1'], cwd=args.output,
               input=(patches/'cudnn-host-dispatch.patch').read_bytes(), check=True)
for relative, hashes in manifest.items():
    assert hashlib.sha256((args.output/relative).read_bytes()).hexdigest() == hashes['patched_sha256']
print(args.output)
