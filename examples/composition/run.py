#!/usr/bin/env python3
"""Measure nested interfaces, held-out inputs, and deliberate negative controls."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
import composition
import explorer
import runner

CONTEXT_MISMATCH = {'context_leaf_raw', 'context_cheap_raw', 'context_expensive_raw'}


def measure(binary, args, out):
    with tempfile.TemporaryDirectory(prefix='.raw-', dir=out) as raw:
        rc, log, files = runner.run([str(binary), *args], raw, timeout=180)
        if rc or not files:
            raise RuntimeError(log)
        model = explorer.build_model(raw, source_root=ROOT,
                                     source_paths=['examples/composition/app.c'], discover=False)
        records, errors = explorer.load_local_traces(explorer.load_raw_runs(Path(raw)))
        assert not errors, errors
    assert model['composition']['status'] == 'observed', model['composition']['errors']
    return model, records


def validate_counts(model, records):
    """Reconstruct observed calls, including U; retain intended context failures.

    This single-thread program has no runtime waiting, so block fits and raw
    invocation totals have matching scope. This is not unseen-cost prediction.
    """
    regions = {r['id']: r for r in model['regions']}
    own_cost = {}
    for name, region in regions.items():
        for point in region['points']:
            own_cost[(name, tuple(point['state']))] = point['recorded']
        for fit in region.get('recordedRegimes', region['regimes']):
            for point in fit['points']:
                assert point['waiting'] == 0
                own_cost[(name, tuple(point['state']))] = point['explained'] + point['unexplained']
    calls = [r for r in records if r['region'] in regions]
    stack, children = [], defaultdict(list)
    for record in sorted(calls, key=lambda r: r['seq']):
        while stack and stack[-1]['seq_end'] < record['seq']:
            stack.pop()
        if stack:
            children[stack[-1]['seq']].append(record)
        stack.append(record)
    predicted, validation = {}, {}
    for record in sorted(calls, key=lambda r: r['seq'], reverse=True):
        name = record['region']
        actual_children = children[record['seq']]
        assert record['incl'] == record['self'] + sum(c['incl'] for c in actual_children)
        state = tuple(record['state'][n] for n in regions[name]['states'])
        estimate = own_cost[(name, state)] + sum(predicted[c['seq']] for c in actual_children)
        predicted[record['seq']] = estimate
        row = validation.setdefault(name, {'calls': 0, 'maxAbsoluteError': 0, 'absoluteError': 0, 'actual': 0})
        error = abs(estimate - record['incl'])
        row['calls'] += 1
        row['maxAbsoluteError'] = max(row['maxAbsoluteError'], error)
        row['absoluteError'] += error
        row['actual'] += record['incl']
    for name, row in validation.items():
        row['relativeAbsoluteError'] = row['absoluteError'] / row['actual']
        row['expectedContextMismatch'] = name in CONTEXT_MISMATCH
        if name in CONTEXT_MISMATCH:
            assert row['relativeAbsoluteError'] > .1, ('negative control disappeared', name, row)
        else:
            assert row['relativeAbsoluteError'] < .05, (name, row)
    return {'scope': 'Observed single-thread reconstruction including tabulated U; not held-out cost prediction',
            'accountingIdentityCalls': len(calls), 'regions': validation}


def assert_cases(model):
    regions = {r['id']: r for r in model['composition']['regions']}
    def edge(name, child=None):
        return next(e for e in regions[name]['children'] if child is None or e['child'] == child)
    def text(name, child=None):
        return composition.edge_text(edge(name, child), regions[name]['states'])
    assert regions['irregular_leaf']['ownUnexplained']
    assert text('repeated') == '(2*n + 1)*F[irregular_leaf]'
    assert text('varying') == '(n)*F[linear_leaf]'
    assert edge('branch_raw')['form'] == 'unresolved'
    assert text('branch_refined') == '(selected_count)*F[irregular_leaf]'
    assert edge('hidden_count')['multiplicity'] is None
    assert [e['child'] for e in regions['three_levels']['children']] == ['middle']
    assert text('three_levels') == '(batches)*F[middle]'
    assert text('middle') == '(n)*F[irregular_leaf]'
    assert regions['recursive']['recursive']
    assert text('multiple_children', 'linear_leaf') == '(n)*F[linear_leaf]'
    assert text('multiple_children', 'irregular_leaf') == '(n + 2)*F[irregular_leaf]'
    assert {e['child'] for e in regions['diamond']['children']} == {'left', 'right'}
    assert text('left') == '(n)*F[linear_leaf]'
    assert text('right') == '(2*n)*F[linear_leaf]'
    assert edge('rectangular_raw')['multiplicity'] is None
    assert text('rectangular_refined') == '(cells)*F[linear_leaf]'
    assert edge('triangular_raw')['multiplicity'] is None
    assert text('triangular_refined') == '(pairs)*F[linear_leaf]'
    assert edge('arguments_raw')['arguments'] is None and edge('arguments_raw')['sequenceArguments'] is None
    assert text('arguments_refined') == '(n)*F[linear_leaf]'
    assert edge('alternating')['arguments'] is None and edge('alternating')['sequenceArguments'] is None
    for name, child in (('mutual_a', 'mutual_b'), ('mutual_b', 'mutual_a')):
        assert regions[name]['recursive']
        assert edge(name)['child'] == child
        assert composition.affine_text(edge(name)['multiplicity'], ['depth', 'more']) == 'more'
    assert text('context_cheap_raw') == '(n)*F[context_leaf_raw]'
    assert text('context_expensive_raw') == '(n)*F[context_leaf_raw]'
    assert text('context_cheap_refined') == '(n)*F[context_leaf_refined]'
    assert text('context_expensive_refined') == '(n)*F[context_leaf_refined]'
    assert text('regime_parent') == '(n)*F[regime_leaf]'
    assert len(regions['regime_leaf']['own']) == 2


def check_frozen(reference, model):
    return composition.check(reference['composition'], model['regions'], model['trace']['events'],
                             model['validity']['errors'] + model['validity']['traceErrors'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--thorough', action='store_true', help='also measure an independently compiled -O0 binary')
    args = parser.parse_args()
    out = ROOT / 'out' / 'composition'
    out.mkdir(parents=True, exist_ok=True)
    os.environ['DRPERF_FOLLOW_THREADS'] = '0'
    def compile_to(path, optimization):
        subprocess.run(['gcc', optimization, '-g', '-Wall', '-Wextra', '-Werror',
                        str(Path(__file__).with_name('app.c')), '-L' + str(ROOT / 'build'),
                        '-lperfmark', '-Wl,-rpath,' + str(ROOT / 'build'), '-o', str(path)], check=True)
    binary = out / 'app'
    compile_to(binary, '-O2')
    baseline, records = measure(binary, [], out)
    assert_cases(baseline)
    summary = {'baseline': validate_counts(baseline, records)}
    baseline['composition']['exampleValidation'] = summary['baseline']
    explorer.write_model(baseline, out / 'composition.drperf.json')
    heldout, records = measure(binary, ['holdout'], out)
    summary['heldoutCounts'] = validate_counts(heldout, records)
    summary['heldoutRelations'] = check_frozen(baseline, heldout)
    assert summary['heldoutRelations']['status'] == 'checked', summary['heldoutRelations']
    assert not summary['heldoutRelations']['newEdges']
    assert not any(e['status'] in ('fails', 'schema-mismatch') for e in summary['heldoutRelations']['edges'])
    explorer.write_model(heldout, out / 'heldout.drperf.json')
    changed, records = measure(binary, ['changed'], out)
    summary['changedCounts'] = validate_counts(changed, records)
    summary['changedRelations'] = check_frozen(baseline, changed)
    failures = [e for e in summary['changedRelations']['edges'] if e['status'] == 'fails']
    assert len(failures) == 1 and failures[0]['parent'] == 'multiple_children' and failures[0]['child'] == 'irregular_leaf', failures
    assert failures[0]['failures'] == 40, failures
    if args.thorough:
        with tempfile.TemporaryDirectory(prefix='.build-', dir=out) as temporary:
            other = Path(temporary) / 'app-O0'
            compile_to(other, '-O0')
            unoptimized, records = measure(other, [], out)
        assert_cases(unoptimized)
        summary['O0Counts'] = validate_counts(unoptimized, records)
        summary['O0Relations'] = check_frozen(baseline, unoptimized)
        assert not summary['O0Relations']['newEdges']
        assert not any(e['status'] in ('fails', 'schema-mismatch') for e in summary['O0Relations']['edges'])
    (out / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    notes = ['\nmeasured validation (observed U included; not unseen-cost prediction)']
    for name in sorted(CONTEXT_MISMATCH | {'context_leaf_refined', 'context_cheap_refined', 'context_expensive_refined'}):
        row = summary['baseline']['regions'][name]
        label = 'EXPECTED FAILURE: hidden caller context' if row['expectedContextMismatch'] else 'refined interface'
        notes.append(f"  {name}: {100*row['relativeAbsoluteError']:.3f}% aggregate absolute reconstruction error; {label}")
    heldout_check = summary['heldoutRelations']
    notes.append(f"  New inputs: {sum(e['checks'] for e in heldout_check['edges'])} frozen relation checks, no failures.")
    notes.append(f"  {sum(e['unresolved'] for e in heldout_check['edges'])} edges still have unexplained child-call multipliers; checking argument relations does not close them.")
    notes.append('  Deliberately changed child count: 40/40 affected parent calls rejected.')
    (out / 'report.txt').write_text('\n'.join(explorer.cost_lines(baseline) + notes) + '\n')
    print(f"PASS: 20 composition cases, {baseline['trace']['recordCount']} baseline calls.")
    print('PASS: frozen relations on new inputs; changed child count detected at all 40 parent calls.')
    print('PASS: raw direct-child accounting; hidden-context negative control fails numerically and refined PCVs fix it.')
    if args.thorough:
        print('PASS: independently compiled -O0 code preserves the checked call relations.')
    print(f"Report: {out / 'report.txt'}")
    print(f"Validation: {out / 'validation.json'}")


if __name__ == '__main__':
    main()
