"""Stage drperf's runtime and Wan markers as a managed-launcher directory asset."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
a.output.mkdir(parents=True, exist_ok=False)
files = [root / 'lib/runner.py']
files += list((root / 'build').glob('*.so'))
files += list((root / 'perfmark/python').glob('*.py'))
files += [root / 'examples/wan_gx' / n for n in ('measure.py', 'instrument.py')]
for directory in ('lib64/release', 'ext/lib64/release'):
    files += list((root / 'third_party/dynamorio' / directory).glob('*.so'))
for source in files:
    target = a.output / source.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
manifest = {str(f.relative_to(a.output)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(a.output.rglob('*')) if f.is_file()}
(a.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(a.output)
