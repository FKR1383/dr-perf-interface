"""Verify and unpack the measured inputs preserved with the Wan timing study."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
a = p.parse_args()
source = Path(__file__).with_name('evidence') / 'timing-inputs'
manifest = json.loads((source / 'manifest.json').read_text())
a.output.mkdir(parents=True, exist_ok=True)
for name, record in manifest.items():
    packed = (source / name).read_bytes()
    assert hashlib.sha256(packed).hexdigest() == record['sha256'], name
    data = gzip.decompress(packed) if name.endswith('.gz') else packed
    assert hashlib.sha256(data).hexdigest() == record['uncompressed_sha256'], name
    assert len(data) == record['uncompressed_bytes'], name
    target = a.output / (name[:-3] if name.endswith('.gz') else name)
    if target.exists():
        assert target.read_bytes() == data, f'Refusing to overwrite different input: {target}'
    else:
        target.write_bytes(data)
print(a.output)
