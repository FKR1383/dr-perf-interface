#!/usr/bin/env python3
"""Check that expansion validation evidence still names the current case assets.

This is an integrity check on saved execution evidence, not a rerun. Source
snapshots are independently checked against Git objects by check_upstream_bytes.
"""
import argparse
import hashlib
import importlib.util
import json
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGIONS = ROOT / 'benchmarks/regions'
loader = importlib.util.spec_from_file_location('collection', REGIONS / 'collect.py')
collection = importlib.util.module_from_spec(loader)
loader.loader.exec_module(collection)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-results', type=Path,
                        default=ROOT / 'benchmarks/growth/compiler-build/entry-final/summary.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'benchmarks/growth/receipt-integrity.json')
    parser.add_argument('--require-verified', action='store_true', help='Require every expansion case to have successful entry evidence')
    args = parser.parse_args()
    failures, checked = [], []
    executions = {}
    for path in (REGIONS / 'general-libraries/validation-executions').glob('*.json'):
        for row in json.loads(path.read_text())['results']:
            executions[row['id']] = row
    sources = [
        ('language-tools', REGIONS / 'language-tools/validation-report.json', 'receipts'),
        ('general-libraries', REGIONS / 'general-libraries/validation-results.json', 'results'),
        ('native-libraries', REGIONS / 'native-libraries/validation.json', None),
        ('compiler-frontends', args.compiler_results, 'results'),
    ]
    for group, evidence_path, key in sources:
        if not evidence_path.is_file():
            failures.append(f'{group}: missing evidence {evidence_path}')
            continue
        document = json.loads(evidence_path.read_text())
        rows = document[key] if key else document
        expected_ids = {p.parent.name for p in (REGIONS / group / 'cases').glob('*/case.json')}
        actual_ids = [r['id'] for r in rows]
        if set(actual_ids) != expected_ids or len(set(actual_ids)) != len(actual_ids):
            failures.append(f'{group}: missing, extra, or duplicate receipt IDs')
        for row in rows:
            case_id = row['id']
            path = REGIONS / group / 'cases' / case_id
            data = json.loads((path / 'case.json').read_text())
            before = len(failures)
            def compare(label, expected, actual):
                if expected != actual:
                    failures.append(f'{case_id}: stale or missing {label}')
            identity = row.get('source', row)
            for name in ('revision', 'path'):
                compare(name, data['source'][name], identity.get(name))
            compare('source SHA', data['source']['sha256'], identity.get('sha256', row.get('source_sha256')))
            compare('snapshot bytes', data['source']['sha256'], sha(path / data['source']['snapshot']))
            compare('region', data['region'], row.get('region'))
            compare('patch', sha(path / 'region.patch'), row.get('patch_sha256'))
            if group == 'native-libraries':
                compare('marker helper', sha(REGIONS / 'support/drperf_bench_region.h'), row.get('marker_helper_sha256'))
            assets = {name: sha(path / name) for name in data['tests']['files']}
            assets.update({r['destination']: sha(path / r['source']) for r in data['tests'].get('resources', [])})
            if group == 'language-tools':
                receipt_assets = {'tests/test_case.py': row.get('test_sha256'), **row.get('resource_sha256', {})}
            else:
                receipt_assets = row.get('test_assets_sha256', row.get('test_sha256', {}))
            compare('test assets', assets, receipt_assets)
            verified = data['tests']['validation']['status'] == 'region-verified'
            if args.require_verified and not verified:
                failures.append(f'{case_id}: region entry is not verified')
            if verified:
                if group == 'language-tools':
                    compare('successful return code', 0, row.get('returncode'))
                    if row.get('marker_hits', 0) <= 0:
                        failures.append(f'{case_id}: no recorded marker entry')
                elif group == 'native-libraries':
                    compare('successful return code', 0, row.get('returncode'))
                    if 'marker and assertions passed' not in row.get('output', ''):
                        failures.append(f'{case_id}: missing native assertion receipt')
                elif group == 'compiler-frontends':
                    compare('verified status', 'region-verified', row.get('status'))
                    fixture_sizes = [r['size'] for r in json.loads((path/'tests/spec.json').read_text())['fixtures']]
                    compare('tested fixture sizes', fixture_sizes, [r['size'] for r in row.get('rows', [])])
                    if not row.get('rows') or any(r.get('returncode') != 0 or r.get('target_entries', 0) <= 0 for r in row['rows']):
                        failures.append(f'{case_id}: missing successful per-size target-entry evidence')
                else:
                    compare('verified status', 'region-verified', row.get('status'))
                    execution = executions.get(case_id, {})
                    compare('executed return code', 0, execution.get('returncode'))
                    compare('executed patch', sha(path / 'region.patch'), execution.get('patch_sha256'))
                    compare('executed test', sha(path / 'tests/test_case.py'), execution.get('test_sha256'))
                    if execution.get('marker_hits', {}).get(case_id, 0) <= 0:
                        failures.append(f'{case_id}: no successful executed marker receipt')
                    with tempfile.TemporaryDirectory(prefix='drperf-receipt-source-') as tmp:
                        marked = collection.apply(path / 'case.json', data, Path(tmp))
                        compare('executed marked source', sha(marked), execution.get('marked_source_sha256'))
            checked.append({'id': case_id, 'group': group, 'status': data['tests']['validation']['status'],
                            'receipt_matches': len(failures) == before})
    report = {'scope': 'Saved evidence integrity; this command does not execute workloads',
              'require_verified': args.require_verified,
              'receipts_checked': len(checked), 'validation_statuses': dict(Counter(r['status'] for r in checked)),
              'failures': failures, 'cases': checked}
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'cases'}))
    return bool(failures)

if __name__ == '__main__':
    raise SystemExit(main())
