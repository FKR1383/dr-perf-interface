"""Index historical fitted regions as review candidates, not validated cases."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def collect(archive):
    regions = {}
    reports = {}
    # Only experiment output directories; do not scan dependencies or model data.
    roots = [archive / 'out', archive / 'videogen' / 'out']
    for root in roots:
        for path in sorted(root.glob('*/derive.txt')):
            content = path.read_text(errors='replace')
            rel = path.relative_to(archive).as_posix()
            reports[rel] = content
            headings = list(re.finditer(r'^derive ([\w.:-]+).*$', content, re.M))
            for i, match in enumerate(headings):
                name = match[1].rstrip(':')
                if name.startswith('_perfmark') or name == 'attach' or name.endswith('_attach'):
                    continue
                system = 'wan' if root.parent.name == 'videogen' else ('ftl' if
                    name.startswith(('ftl_', 'case_', 'hm_', 'vllm_admission_', 'vllm_compaction_',
                                     'vllm_store_', 'vllm_lease_', 'vllm_routing_', 'vllm_spec_')) else 'vllm')
                key = system + ':' + name
                region = regions.setdefault(key, {
                    'id': hashlib.sha256(key.encode()).hexdigest()[:12],
                    'system_hint': system, 'region': name,
                    'status': 'needs-review', 'evidence': [],
                    'review_required': ['identify exact source region and pre-fix revision',
                        'deduplicate aliases and overlapping probes',
                        'remove empty measurement controls',
                        'audit trace validity and unexplained cost',
                        'construct independent input changes and held-out fixtures',
                        'review executable PCV oracle and annotation cost',
                        'prepare clean workload and test both measurement modes'],
                })
                end = headings[i+1].start() if i+1 < len(headings) else len(content)
                block = content[match.start():end]
                region['evidence'].append({
                    'report': rel, 'start_line': content[:match.start()].count('\n')+1,
                    'end_line': content[:end].count('\n'),
                    'formula_lines': re.findall(r'^  cost\(.*$', block, re.M),
                    'irregular_shares_percent': [float(x) for x in re.findall(r'irregular \(([\d.]+)% of cost\)', block)],
                    'insufficient_states': 'only ' in match[0] and 'state point' in match[0],
                })
    return sorted(regions.values(), key=lambda r: (r['system_hint'], r['region'])), reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[1]/'evaluator')
    args = parser.parse_args()
    regions, reports = collect(args.archive.resolve())
    args.destination.mkdir(parents=True, exist_ok=True)
    for rel, content in reports.items():
        dest = args.destination / 'region-reports' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    (args.destination/'region-candidates.json').write_text(json.dumps({
        'schema_version': 1, 'scored_cases': 0,
        'warning': 'Region names are candidates, not distinct validated cases. Historical annotations are hypotheses, not automatically ground truth. System labels are heuristic. Null probes, fixed variants and aliases are intentionally retained for review.',
        'report_hashes': {p:hashlib.sha256(c.encode()).hexdigest() for p,c in reports.items()},
        'candidates': regions,
    }, indent=2)+'\n')
    print(f'{len(regions)} review candidates from {len(reports)} reports; no cases promoted automatically.')


if __name__ == '__main__':
    main()
