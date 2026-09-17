#!/usr/bin/env python3
"""Recompute instruction reductions from the accepted, same-state measurements."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
report = {'scope': 'Measured target instructions on identical recorded states; no agent accuracy or full-system throughput claim', 'cases': []}
for case_id in ('aq-003', 'vllm-024'):
    workspace = ROOT / 'bench_optimized/growth-multifold' / case_id
    result = json.loads((workspace / 'result.json').read_text())
    assert result['status'] == 'accepted', case_id
    paths = [(workspace / result[name]).resolve() for name in ('baseline_measurement', 'optimized_measurement')]
    before, after = [str(p.parent.relative_to(ROOT)) for p in paths]
    metrics = [json.loads(p.read_text()) for p in paths]
    assert all(m['returncode'] == 0 and m['gate_pass'] for m in metrics), case_id
    def key(row):
        return tuple(sorted(row['state'].items()))
    baseline = {key(r): r for r in metrics[0]['states']}
    optimized = {key(r): r for r in metrics[1]['states']}
    assert baseline.keys() == optimized.keys(), f'{case_id}: different observed states'
    rows = []
    for state in baseline:
        b, a = baseline[state], optimized[state]
        assert b['calls'] == a['calls'], f'{case_id}: different call multiplicities'
        rows.append({'state': b['state'], 'calls': b['calls'],
                     'before_instructions_per_call': b['instructions_per_call'],
                     'after_instructions_per_call': a['instructions_per_call'],
                     'instruction_ratio': b['instructions_per_call'] / a['instructions_per_call']})
    bt = sum(r['calls'] * r['before_instructions_per_call'] for r in rows)
    at = sum(r['calls'] * r['after_instructions_per_call'] for r in rows)
    report['cases'].append({'id': case_id, 'baseline': before, 'optimized': after,
                           'metrics_sha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
                           'baseline_max_unexplained_share': metrics[0]['max_unexplained_share'],
                           'optimized_max_unexplained_share': metrics[1]['max_unexplained_share'],
                           'baseline_total_instructions': bt, 'optimized_total_instructions': at,
                           'weighted_instruction_ratio': bt / at, 'states': rows})
(ROOT / 'benchmarks/growth/performance-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({r['id']: r['weighted_instruction_ratio'] for r in report['cases']}))
