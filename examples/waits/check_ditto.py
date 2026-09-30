#!/usr/bin/env python3
"""Run real-capture ablations of Ditto's wait indicators; never edits the capture."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
import wait_contracts

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('profile')
parser.add_argument('-o', '--output', default=str(ROOT / 'out/waits/ditto-contract-check.json'))
args = parser.parse_args()
raw = Path(args.profile).read_bytes()
model = json.loads(raw)
declarations = json.loads((Path(__file__).parent / 'ditto_contracts.json').read_text())
result = wait_contracts.check(model, declarations)
assert all(c['status'] == 'verified-observed' for c in result['claims'])
assert result['coverage']['explainedOperations'] == 43
assert result['coverage']['unexplainedOperations'] == 16576
assert result['status'] == 'incomplete'  # CUDA coverage must not hide unknown locks.
ablations = {}
for label, indicator, producer, expected in [
    ('always', 'True', 'carrier.transfer', (0, 5, 0)),
    ('never', 'False', 'carrier.transfer', (9, 0, 0)),
    ('reversed', 'd2h == 0', 'carrier.transfer', (9, 5, 0)),
    ('wrong-producer', 'd2h == 1', 'codec.encode_units', (0, 0, 9)),
]:
    altered = copy.deepcopy(declarations)
    altered['claims'][0].update(indicator=indicator, producer=producer)
    checked = wait_contracts.check(model, altered)
    row = checked['claims'][0]
    assert checked['status'] == 'invalid'
    assert (row['unexpectedPresence'], row['unexpectedAbsence'], row['producerMismatches']) == expected
    ablations[label] = row
    print(f"{label}: {expected[0]} omitted waits, {expected[1]} predicted-but-absent waits, {expected[2]} wrong producers")
omitted = copy.deepcopy(declarations); omitted['claims'].pop(0)
checked = wait_contracts.check(model, omitted)
missing = next(r for r in checked['unexplained'] if r['region'] == 'carrier.transfer' and r['api'] == 'cudaStreamWaitEvent')
assert missing['operations'] == 9
ablations['omitted-declaration'] = missing
unknown = copy.deepcopy(declarations)
unknown['claims'].append(dict(id='lock-needs-owner', region='ftl.lock', api='pthread_mutex_lock', indicator='True', producer='store.drain'))
checked = wait_contracts.check(model, unknown)
row = checked['claims'][-1]
assert row['indicatorStatus'] == 'verified-observed' and row['producerStatus'] == 'unverified'
ablations['unsupported-owner-attribution'] = row
out = dict(profile=str(Path(args.profile).resolve()), profileSha256=hashlib.sha256(raw).hexdigest(),
           declarations=declarations, result=result, ablations=ablations)
output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(out, indent=2)+'\n')
print(f"Correct declarations: 43 explained CUDA operations; 16576 mutex/semaphore operations remain unexplained.\n{output}")
