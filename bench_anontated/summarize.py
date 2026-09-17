#!/usr/bin/env python3
"""Build review indexes from recorded case outcomes without changing benchmarks."""
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def main():
    annotations, optimizations = [], []
    for manifest in sorted((ROOT/'benchmarks/regions').glob('*/cases/*/case.json')):
        case = read(manifest)
        group = manifest.relative_to(ROOT/'benchmarks/regions').parts[0]
        ann_dir = ROOT/'bench_anontated'/group/case['id']
        opt_dir = ROOT/'bench_optimized'/group/case['id']
        result = read(ann_dir/'result.json') if (ann_dir/'result.json').exists() else {}
        measurements = [read(p) for p in ann_dir.rglob('metrics.json')]
        annotations.append({'case': case['id'], 'group': group,
                            'status': result.get('status', 'pending'),
                            'gate_pass': bool(result.get('gate_pass')),
                            'has_drperf_trace': any(m.get('raw_files') for m in measurements),
                            'valid_target_measurement': any(m.get('returncode') == 0 and
                                not m.get('validity_warnings') and m.get('states') and m.get('calls', 0) > 0
                                for m in measurements),
                            'measurement_records': len(measurements),
                            'result': str((ann_dir/'result.json').relative_to(ROOT)),
                            'final_measurement': result.get('final_measurement')})
        result = read(opt_dir/'result.json') if (opt_dir/'result.json').exists() else {}
        row = {'case': case['id'], 'group': group, 'status': result.get('status', 'pending'),
               'accepted': bool(result.get('accepted')),
               'result': str((opt_dir/'result.json').relative_to(ROOT))}
        if row['accepted']:
            before = read((opt_dir/result['baseline_measurement']).resolve())
            after = read((opt_dir/result['optimized_measurement']).resolve())
            b = sum(s['instructions_per_call']*s['calls'] for s in before['states'])
            a = sum(s['instructions_per_call']*s['calls'] for s in after['states'])
            row.update(baseline_instructions=b, optimized_instructions=a,
                       instruction_reduction_fraction=1-a/b if b else None,
                       baseline_gate_pass=before['gate_pass'], optimized_gate_pass=after['gate_pass'])
            before_states = {json.dumps(s['state'], sort_keys=True): s for s in before['states']}
            after_states = {json.dumps(s['state'], sort_keys=True): s for s in after['states']}
            row['same_states_and_calls'] = (before_states.keys() == after_states.keys() and
                all(before_states[k]['calls'] == after_states[k]['calls'] for k in before_states))
            if row['same_states_and_calls']:
                row['regressed_states'] = [before_states[k]['state'] for k in before_states
                    if after_states[k]['instructions_per_call'] > before_states[k]['instructions_per_call']]
        optimizations.append(row)
    ann = {'cases': annotations, 'case_count': len(annotations),
           'status_counts': dict(Counter(c['status'] for c in annotations)),
           'qualified_cases': sum(c['gate_pass'] for c in annotations),
           'cases_attempted': sum(c['measurement_records'] > 0 for c in annotations),
           'cases_with_valid_target_measurements': sum(c['valid_target_measurement'] for c in annotations),
           'cases_with_drperf_traces': sum(c['has_drperf_trace'] for c in annotations)}
    opt = {'cases': optimizations, 'case_count': len(optimizations),
           'status_counts': dict(Counter(c['status'] for c in optimizations)),
           'accepted_count': sum(c['accepted'] for c in optimizations)}
    write(ROOT/'bench_anontated/summary.json', ann)
    write(ROOT/'bench_optimized/summary.json', opt)
    lines = ['# Recorded agent experiment results', '',
             f"{ann['case_count']} case exports; {ann['cases_attempted']} cases attempted; "
             f"{ann['cases_with_valid_target_measurements']} have successful target measurements; "
             f"{ann['qualified_cases']} final annotations pass the gate.", '',
             '| Group | Cases | Successful target measurements | Final gate passes |',
             '| --- | ---: | ---: | ---: |']
    for group in sorted({c['group'] for c in annotations}):
        cs = [c for c in annotations if c['group'] == group]
        lines.append(f"| {group} | {len(cs)} | {sum(c['valid_target_measurement'] for c in cs)} | {sum(c['gate_pass'] for c in cs)} |")
    lines += ['', '## Accepted optimizations', '',
              '| Case | Before instructions | After instructions | Reduction | Optimized model passes 5% gate | Small-state regressions |',
              '| --- | ---: | ---: | ---: | --- | --- |']
    for c in optimizations:
        if c['accepted']:
            lines.append(f"| [{c['case']}](../{c['result']}) | {c['baseline_instructions']:,.0f} | "
                         f"{c['optimized_instructions']:,.0f} | {100*c['instruction_reduction_fraction']:.2f}% | "
                         f"{'Yes' if c['optimized_gate_pass'] else 'No; needs further explanation'} | "
                         f"{'Yes; see per-state evidence' if c.get('regressed_states') else 'None observed'} |")
    lines += ['', 'These are total target-region instructions over matching small workloads, not',
              'end-to-end latency improvements or larger-input predictions. Rejected candidates',
              'remain in the optimization directory with `accepted: false`.', '',
              'The CSV candidate aq-008 was rejected after differential tests found changed',
              'behavior. The vLLM bulk-queue candidate vllm-024 regressed on its measured workload.',
              'Exploratory agents had prior collection context; this is not a blinded accuracy comparison.', '',
              'See `summary.json` in each experiment directory for every outcome, including',
              'blocked, failed, above-threshold, and unattempted cases. The audit checks that',
              'benchmark files and marked boundaries are preserved and final measurements match source hashes.', '']
    (ROOT/'bench_anontated/RESULTS.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in ann.items() if k != 'cases'}))
    print(json.dumps({k:v for k,v in opt.items() if k != 'cases'}))


if __name__ == '__main__':
    main()
