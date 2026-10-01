"""Check passive declared event order, without inferring application predicates.

Event IDs/generations are supplied by the annotator. Publication is a checkpoint
immediately before the real release. Waited follows the existing readiness check.
Neither checkpoint implements a wait; explicit probes may delay publication.
"""
from collections import defaultdict, Counter
import math

import composition
import waits
from report_storage import require_inline_waits

# Legacy end checkpoints remain readable; begin is no longer required.
DECLARED = {'declared_publish', 'declared_waited', 'declared_wait_end'}
WAITED = {'declared_waited', 'declared_wait_end'}


def check(model):
    require_inline_waits(model)
    capture = model.get('waits') or {}
    captured = capture.get('events', [])
    events = [e for e in captured if e['kind'] in DECLARED]
    if not events:
        return None
    original_names = {r['id']: r.get('originalName', r['id']) for r in model.get('regions', [])}
    probe = waits.validate_delay_probes(captured, model.get('provenance', {}).get('runs', []),
                                        original_names)
    out = {'status': 'unverified', 'probe': probe['actual'] or bool(capture.get('probe')),
           'probeRequested': probe['requested'] or bool(capture.get('probeRequested')), 'edges': [],
           'violations': [], 'unverified': [], 'unexplained': [], 'interfaces': [],
           'contract': 'Observed CPU checkpoint order, not proof of necessary dependency. '
                       'No condition argument: markers follow original control flow. '
                       'Publish precedes the real release; waited follows observed readiness. '
                       'IDs/generations are process-scoped. GPU submission alone is not GPU completion.'}
    if probe['warnings']:
        out['unverified'].extend({'reason': reason} for reason in probe['warnings'])
        return out
    if (capture.get('status') != 'observed' or capture.get('warnings')
            or not model.get('trace', {}).get('complete')
            or model.get('validity', {}).get('errors') or model.get('validity', {}).get('traceErrors')):
        specific = probe['warnings'] or [w for w in capture.get('warnings', [])
                                         if 'delay' in w.lower() or 'probe' in w.lower()]
        out['unverified'].extend({'reason': reason} for reason in specific)
        out['unverified'].append({'reason': 'Incomplete capture; ordering and coverage cannot be checked.'})
        return out
    counts = Counter(e['group'] for e in captured)
    for index, run in enumerate(model.get('provenance', {}).get('runs', [])):
        measurement = run.get('measurement', {})
        if 'wait_records' not in measurement:  # Portable reports predating record metadata.
            continue
        group = f'{index}:{measurement.get("pid", 0)}'
        if measurement.get('wait_dropped') or counts[group] != measurement['wait_records']:
            out['unverified'].append({'reason':
                'Synchronization record count differs from capture metadata.'})
            return out
    regions = {r['id']: r for r in model['regions']}
    traces = model['trace']['events']
    composition._forest(regions, traces)
    by_call = {(t['group'], str(t['thread']), composition._integer(t['seq'])): t for t in traces}
    canonical = []
    for original in events:
        e = dict(original)
        e['regionSeq'] = composition._integer(e['regionSeq'])
        invocation = (e['group'], str(e['tid']), e['regionSeq'])
        parent = by_call.get(invocation)
        valid = True
        if parent is None:
            valid = False
            out['unverified'].append({'checkpoint': e['id'], 'reason':
                'Event checkpoint is outside a captured region invocation.'})
            e['region'] = ''
        else:
            e['region'] = parent['region']
        if not e.get('returned') or e.get('result') != 0 or e['end'] <= e['start']:
            valid = False
            out['unverified'].append({'checkpoint': e['id'], 'reason': 'Incomplete event checkpoint'})
        e['_valid'] = valid
        canonical.append(e)
    events = canonical
    publications = defaultdict(list)
    def key(e): return e['group'], str(e['object']), str(e['aux'])
    def thread(e): return e['group'], str(e['tid'])
    ids = [e['id'] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate event checkpoint ID')
    for e in events:
        if e['kind'] == 'declared_publish' and e['_valid']:
            publications[key(e)].append(e)
    for identity, pubs in publications.items():
        if len(pubs) != 1:
            out['violations'].append({'event': list(identity), 'reason': 'Event generation published more than once',
                                      'publications': [p['id'] for p in pubs]})
    for e in sorted(events, key=lambda e: (e['group'], e['start'])):
        if e['kind'] not in WAITED:
            continue
        pubs = publications[key(e)]
        edge = {'event': str(e['object']), 'generation': str(e['aux']), 'group': e['group'],
                'consumer': e['region'], 'consumerInvocation': e['regionSeq'],
                'waited': e['id'], 'status': 'unverified',
                'producer': None, 'publication': None}
        if not e['_valid']:
            out['edges'].append(edge)
            continue
        if len(pubs) == 1:
            pub = pubs[0]
            edge.update(producer=pub['region'], publication=pub['id'], producerInvocation=pub['regionSeq'])
            if pub['end'] < e['start']:
                edge['status'] = 'ordered'
                if 'beginUs' in e and 'endUs' in pub:
                    edge['distanceUs'] = max(0, int(e['beginUs'])-int(pub['endUs']))
            else:
                edge['status'] = 'violation'
                out['violations'].append({'event': list(key(e)), 'consumer': e['region'],
                    'producer': pub['region'], 'waited': e['id'], 'publication': pub['id'],
                    'reason': 'Consumer passed waited before declared publication completed'})
        else:
            out['unverified'].append({'event': list(key(e)), 'waited': e['id'],
                                      'reason': 'Missing or ambiguous publication generation'})
        out['edges'].append(edge)
    # Declaration ownership follows the captured invocation containing waited,
    # irrespective of which descendant implements the native synchronization.
    # Record that context without claiming a native object/publication match.
    parents = {}
    stacks = defaultdict(list)
    for call in sorted(traces, key=lambda t: (t['group'], int(t['seq']))):
        identity = (call['group'], str(call['thread']), int(call['seq']))
        stack = stacks[identity[:2]]
        while stack and int(stack[-1]['end']) < int(call['seq']):
            stack.pop()
        parents[identity] = ((stack[-1]['group'], str(stack[-1]['thread']), int(stack[-1]['seq']))
                             if stack else None)
        stack.append(call)
    declarations = defaultdict(list)
    checkpoints = {e['id']: e for e in events}
    for edge in out['edges']:
        e = checkpoints[edge['waited']]
        if e['_valid']:
            declarations[e['group'], str(e['tid']), e['regionSeq']].append(edge)
        edge['nativeContext'] = []
    contexts = defaultdict(Counter)
    unknown = defaultdict(list)
    known_count = 0
    for op in capture.get('operations', []):
        invocation = (op['group'], str(op['tid']), int(op['regionSeq']))
        call = by_call.get(invocation)
        if call is None:
            continue
        # Canonicalize the region from its actual invocation, as for checkpoints.
        region = call['region']
        current = invocation
        while current is not None:
            for edge in declarations[current]:
                marker = checkpoints[edge['waited']]
                if op.get('returned') and 0 < int(op.get('end', 0)) < int(marker['start']):
                    contexts[edge['waited']][region, op['api']] += 1
            current = parents[current]
        if op.get('producers'):
            known_count += 1
        else:
            unknown[region, op['api']].append(op)
    for edge in out['edges']:
        edge['nativeContext'] = [dict(region=region, api=api, count=count)
                                for (region, api), count in sorted(contexts[edge['waited']].items())]
    for (region, api), ops in sorted(unknown.items()):
        out['unexplained'].append({'region': region, 'api': api, 'count': len(ops),
                                  'term': 'unexplained(Wait[?])', 'examples': [o['id'] for o in ops[:3]]})
    out['nativeResolved'] = known_count
    out['coverage'] = ('Native publisher resolution and declared event order are separate checks. '
                       'nativeContext lists preceding synchronization in the declaring invocation '
                       'or its descendants; it is context, not a claim that the declaration covers '
                       'every listed operation. A shared primitive needs no semantic region of its own.')
    # Infer only occurrence counts from existing entry PCVs. No new condition is
    # supplied or evaluated by the marker, and identical states are not averaged.
    buckets = defaultdict(Counter)
    for e in events:
        if e['kind'] in WAITED and e['_valid'] and e['region'] in regions:
            buckets[e['region'], str(e['object'])][e['group'], str(e['tid']), e['regionSeq']] += 1
    for (region, event), counts in sorted(buckets.items()):
        calls = [t for t in traces if t['region'] == region]
        names = regions[region]['states']
        values = [counts[t['group'], str(t['thread']), t['seq']] for t in calls]
        relation = composition.affine([[composition._integer(t['values'][n]) for n in names] for t in calls], values, names)
        out['interfaces'].append({'region': region, 'event': event, 'states': names,
            'countFormula': relation, 'present': sum(v > 0 for v in values), 'absent': sum(v == 0 for v in values)})
    out['status'] = 'violation' if out['violations'] else 'unverified' if out['unverified'] else 'ordered'
    return out


def probe_plan(report, margin_ms=100, maximum_ms=5000):
    """Plan a second execution; distance is diagnostic wall time, never cost."""
    if margin_ms < 1 or maximum_ms < margin_ms:
        raise ValueError('Probe bounds must be positive and maximum >= margin')
    if not report or report['probe']:
        raise ValueError('Plan from an unperturbed event capture')
    gaps = defaultdict(list)
    for edge in report['edges']:
        if edge['status'] == 'ordered' and edge['producer'] and 'distanceUs' in edge:
            gaps[edge['producer']].append(edge['distanceUs'])
    return [{'region': region, 'delayMs': min(maximum_ms, math.ceil(max(values)/1000)+margin_ms),
             'baselineMaxDistanceUs': max(values),
             'capped': math.ceil(max(values)/1000)+margin_ms > maximum_ms,
             'scope': 'all declared publications in this region; rerun one region per probe'}
            for region, values in sorted(gaps.items())]
