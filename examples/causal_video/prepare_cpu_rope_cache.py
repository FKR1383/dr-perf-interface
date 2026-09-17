"""Create an isolated, opt-in Inferix RoPE frequency-cache variant.

Use INFERIX_ROPE_FREQ_CACHE=1 to enable the cache. The source tree is never
modified; callers must select the emitted tree explicitly with --tree.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PATCH = Path(__file__).resolve().parent / 'cpu_patches/rope_frequency_cache.patch'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path,
                        default=ROOT / 'out/causal-video/Inferix-optimized')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'out/causal-video/Inferix-cpuopt')
    args = parser.parse_args()
    base = args.base.resolve()
    output = args.output.resolve()
    if output.exists():
        parser.error(f'output already exists: {output}')
    if not (base / 'inferix/models/self_forcing/causal_model.py').is_file():
        parser.error(f'not an Inferix source tree: {base}')
    shutil.copytree(base, output)
    try:
        subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(PATCH)],
                       cwd=output, check=True)
    except Exception:
        shutil.rmtree(output)
        raise
    print(output)


if __name__ == '__main__':
    main()
