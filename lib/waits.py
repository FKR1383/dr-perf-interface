"""Observed synchronization interfaces, without wait annotations.

API semantics identify wait operations. Durations and syscall attempts never
prove sleeping. Only a deliberately narrow set of producer mappings is resolved;
all other operations remain visible with an unresolved dependency.
"""
from collections import Counter, defaultdict
from pathlib import Path
import json

import composition

WAIT_KINDS = {'completion', 'lock', 'condition', 'join', 'receive',
              'event_wait', 'stream_wait', 'device_wait', 'stream_dependency'}


def validate_delay_probes(events, runs, original_names=None):
    """Validate new probe metadata; legacy runs without it remain readable."""
    requests, warnings = {}, []
    original_names = original_names or {}
    def region(event):
        return original_names.get(event.get('region'), event.get('region'))
    for index, run in enumerate(runs):
        meta = run.get('measurement', run.get('data', {}).get('drperf', {}))
        if not all(k in meta for k in
                   ('wait_delay_region', 'wait_delay_kind', 'wait_delay_injections')):
            continue
        group = f'{index}:{meta.get("pid", 0)}'
        injected = [e for e in events if e.get('group') == group and e.get('injectedDelayMs', 0)]
        if int(meta.get('wait_delay_injections', 0)) != len(injected):
            warnings.append(f'{group}: delay injection count differs from capture metadata')
        if int(meta.get('wait_delay_ms', 0)) > 0:
            requests[group] = (meta.get('wait_delay_kind'), meta.get('wait_delay_region'),
                               int(meta['wait_delay_ms']))
        expected = requests.get(group)
        expected_kind = ('declared_publish' if expected and expected[0] == 'event'
                         else 'sem_publish')
        if any(not expected or int(e.get('injectedDelayMs', 0)) != expected[2]
               or region(e) != expected[1] or e.get('kind') != expected_kind
               or not e.get('returned') or not e.get('end') for e in injected):
            warnings.append(f'{group}: injected delay records are inconsistent or incomplete')
    for request in sorted(set(requests.values())):
        groups = {group for group, value in requests.items() if value == request}
        expected_kind = 'declared_publish' if request[0] == 'event' else 'sem_publish'
        matched = any(e.get('group') in groups and e.get('kind') == expected_kind
                      and region(e) == request[1]
                      and int(e.get('injectedDelayMs', 0)) == request[2]
                      for e in events)
        if not matched:
            warnings.append('Requested delay probe did not execute for '
                            f'{request[0]} publication in region {request[1]}.')
    actual = any(e.get('injectedDelayMs', 0) for e in events)
    return {'requested': bool(requests) or actual, 'actual': actual, 'warnings': warnings}


def succeeded(event):
    if not event.get('returned', False):
        return False
    result = event.get('result')
    return result >= 0 if event.get('kind') == 'receive' else result == 0


def analyze(events, complete=True):
    """Resolve only complete semaphore lifetimes and recorded CUDA events.

    Semaphore mapping requires initial zero tokens and exactly one successful
    publication and consumption in a closed lifetime. Multiple possible token
    sources are left unresolved. This is dependency evidence, not a sleep test.
    """
    operations = []
    objects = defaultdict(list)
    transfers = defaultdict(list)
    unfinished_objects = set()
    for event in events:
        objects[(event['group'], event['object'])].append(event)
        if not event.get('returned') or not event['end']:
            unfinished_objects.add((event['group'], event['object']))
        if event['kind'] == 'transfer':
            transfers[event['group'], event['object']].append(event)
    for event in events:
        if event['kind'] not in WAIT_KINDS:
            continue
        item = dict(event, dependency='unresolved', producers=[],
                    blocking='unknown', reason='Producer mapping is unsupported or unobserved.')
        if not complete:
            item['reason'] = 'Incomplete observation; producer mappings disabled.'
        elif ((event['group'], event['object']) in unfinished_objects or
              (event['kind'] == 'stream_dependency' and
               (event['group'], event['aux']) in unfinished_objects)):
            item['reason'] = 'Object has unfinished synchronization calls; producer mapping is unresolved.'
        elif event['kind'] == 'receive':
            result = event.get('result')
            if result > 0:
                item.update(receiveStatus='data', reason=
                    'Receive returned data; its remote producer is not observable in this capture.')
            elif result == 0:
                item.update(receiveStatus='zero-bytes', reason=
                    'Receive returned zero bytes (EOF or an empty receive); remote state is unresolved.')
            else:
                item.update(receiveStatus='error', reason='Receive returned an error.')
        elif not succeeded(event):
            item['reason'] = 'Call did not return success.'
        elif event['kind'] == 'completion':
            timeline = objects[event['group'], event['object']]
            initializers = [r for r in timeline if r['kind'] == 'sem_init' and
                            succeeded(r) and r['end'] < event['start']]
            if initializers:
                init = max(initializers, key=lambda r: r['end'])
                boundaries = [r for r in timeline if r['kind'] in ('sem_destroy', 'sem_init')
                              and succeeded(r) and r['start'] > init['end']]
                end = min((r['start'] for r in boundaries), default=float('inf'))
                lifetime = [r for r in timeline if init['end'] < r['start'] < end]
                posts = [r for r in lifetime if r['kind'] == 'sem_publish' and succeeded(r)]
                waits = [r for r in lifetime if r['kind'] in ('completion', 'sem_consume') and succeeded(r)]
                if (init.get('processShared') is False and int(init['aux']) == 0 and len(posts) == len(waits) == 1
                        and posts[0]['start'] < event['end'] and end != float('inf')):
                    item.update(dependency='matched-completion', producers=[posts[0]['id']],
                                reason='Zero-initialized closed semaphore lifetime; unique successful post/wait.')
                    item['ordering'] = ('publication-returned-before-wait' if posts[0]['end'] < event['start']
                                        else 'publication-overlapped-wait')
                elif init.get('processShared') is not False:
                    item['reason'] = 'Process-local semaphore ownership was not established.'
                elif int(init['aux']) > 0:
                    item['reason'] = 'Initial tokens can satisfy this wait without a producer.'
                else:
                    item['reason'] = 'Semaphore lifetime is open or token provenance is ambiguous.'
        elif event['kind'] in ('event_wait', 'stream_dependency'):
            # StreamWaitEvent queues a dependency without blocking the CPU.
            handle = event['aux'] if event['kind'] == 'stream_dependency' else event['object']
            timeline = objects[event['group'], handle]
            # Event handles can be reused, and each record replaces the captured work.
            preceding = [r for r in timeline if r['kind'] in ('event_create', 'event_destroy', 'event_record')
                         and succeeded(r) and r['end'] < event['start']]
            overlapping = [r for r in timeline if r['kind'] in ('event_create', 'event_destroy', 'event_record')
                           and r['start'] < event['end'] and r['end'] >= event['start']]
            creations = [r for r in preceding if r['kind'] in ('event_create', 'event_destroy')]
            creation = max(creations, key=lambda r: r['end']) if creations else None
            private = creation and creation['kind'] == 'event_create' and not (int(creation['aux']) & 4)
            if preceding and not overlapping and private:
                record = max(preceding, key=lambda r: r['end'])
                if record['kind'] == 'event_record' and record['start'] > creation['end']:
                    item.update(dependency='matched-event-record', producers=[record['id']],
                                reason='Successful event wait matches the latest observed record generation.')
                    item['stream'] = record['aux']
                    if event['kind'] == 'stream_dependency':
                        item['reason'] = 'Queued stream dependency matches the latest observed event-record generation.'
                        item['consumerStream'] = event['object']
                        item['blocking'] = 'not-a-host-wait'
        elif event['kind'] == 'stream_wait' and int(event['object']) > 2:
            timeline = objects[event['group'], event['object']]
            boundaries = [r for r in timeline if r['kind'] in ('stream_create', 'stream_destroy', 'stream_wait')
                          and succeeded(r) and r['end'] < event['start']]
            previous = max(boundaries, key=lambda r: r['end']) if boundaries else None
            lower = previous['end'] if previous else 0
            # Stream destruction/reuse without an observed create is ambiguous.
            if not previous or previous['kind'] != 'stream_destroy':
                copies = [r for r in transfers[event['group'], event['object']]
                          if succeeded(r) and lower < r['start'] and r['end'] < event['start']]
                if copies:
                    item.update(dependency='observed-stream-prefix', producers=[r['id'] for r in copies],
                                reason='Observed transfers submitted to this explicit stream since the last '
                                       'completed sync/create; kernels and imported dependencies may be missing.')
                    item['stream'] = event['object']
        operations.append(item)
    return operations


def build(runs, regions, traces, errors=()):
    events, warnings, captures = [], list(errors), []
    unattributed = Counter()
    for index, run in enumerate(runs['runs']):
        meta = run['data'].get('drperf', {})
        if not meta.get('waits_enabled'):
            continue
        captures.append(meta)
        for api, counts in meta.get('wait_unattributed', {}).items():
            if counts['kind'] in WAIT_KINDS:
                unattributed[api] += counts['calls']
        path = Path(runs['path']) / (run['file'] + '.waits')
        try:
            records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        except (OSError, ValueError) as error:
            warnings.append(f'{run["file"]}: missing or unreadable wait sidecar: {error}')
            continue
        if len(records) != meta.get('wait_records') or meta.get('wait_dropped'):
            warnings.append(f'{run["file"]}: synchronization records missing or dropped')
        group = f'{index}:{meta.get("pid", 0)}'
        for r in records:
            r.update(group=group, id=f'{group}:{r["start"]}')
            events.append(r)
    probe = validate_delay_probes(events, runs['runs'])
    warnings.extend(probe['warnings'])
    if not captures:
        return None
    if len(captures) != len(runs['runs']):
        warnings.append('Wait capture was not enabled in every process.')
    # Region source schemas are already canonicalized by the main exporter.
    parents = {(t['group'], str(t['thread']), int(t['seq'])): t for t in traces}
    for event in events:
        parent = parents.get((event['group'], str(event['tid']), event['regionSeq']))
        if parent:
            event['region'] = parent['region']
    # Background workers can still be waiting when a successful process exits.
    # Retain these observations, but do not invalidate unrelated, completed
    # region histories. analyze() disables mappings for every affected object.
    pending = [e for e in events if not e['end'] or not e['returned']]
    schemas = {r['id']: r['states'] for r in regions}
    if any(e['region'] in schemas for e in pending):
        warnings.append('Some synchronization calls inside application regions did not return normally.')
    operations = analyze(events, complete=not warnings)
    counts = Counter((r['group'], str(r['tid']), r['regionSeq'], r['api']) for r in operations)
    summaries = []
    grouped = defaultdict(list)
    for op in operations:
        grouped[op['region'], op['api'], op['kind']].append(op)
    for (region, api, kind), observed in sorted(grouped.items()):
        calls = [t for t in traces if t['region'] == region]
        states = schemas.get(region, [])
        rows = [tuple(int(t['values'][n]) for n in states) for t in calls]
        values = [counts[t['group'], str(t['thread']), int(t['seq']), api] for t in calls]
        mapped = sum(values) == len(observed)
        relation = composition.affine(rows, values, states) if calls and mapped and not warnings else None
        summaries.append({'region': region, 'api': api, 'kind': kind, 'calls': len(observed),
                          'parentCalls': len(calls), 'states': states, 'countFormula': relation,
                          'matched': sum(bool(r['producers']) for r in observed),
                          'unresolved': sum(not r['producers'] for r in observed),
                          'potentialSyscalls': sum(r['potentialSyscalls'] for r in observed),
                          'elapsedUs': sum(r['elapsedUs'] for r in observed)})
    return {'status': 'partial' if warnings else 'observed', 'warnings': warnings,
            'pendingCalls': [{'id': e['id'], 'region': e['region'], 'api': e['api'],
                              'object': e['object']} for e in pending],
            'unattributedOperations': dict(unattributed),
            'probeRequested': probe['requested'],
            'probe': probe['actual'],
            'coverage': 'Wrapped libc synchronization/socket APIs and selected CUDA runtime APIs; '
                        'unmarked libc housekeeping is aggregated; semaphore/CUDA object history is retained. '
                        'outer API only. Custom atomics, raw syscalls, CUDA driver-only calls and '
                        'native GX internals are not fully observed. Late attach misses earlier operations.',
            'contract': 'Observed operation counts and conservative object-based dependency evidence. '
                        'API elapsed time and syscall attempts do not establish sleeping or native latency. '
                        'Matched CUDA producers identify submitted stream work, not CPU completion of the launch region. '
                        'Stream-prefix matches are partial; unobserved kernels/dependencies can also be required.',
            'regions': summaries, 'operations': operations, 'events': events}


def lines(report):
    if not report:
        return []
    out = ['native synchronization observations (instrumented evidence, not semantic dependency declarations or latency):']
    if report['probe']:
        out.append('  DELAY PROBE: perturbed execution; keep separate from baseline cost fits.')
    by_id = {r['id']: r for r in report['events']}
    for row in report['regions']:
        relation = row['countFormula']
        count = composition.affine_text(relation, row['states']) if relation else '?'
        out.append(f'  {row["region"] or "<outside regions>"}: {row["api"]} [{row["kind"]}] '
                   f'{row["calls"]} calls; per-region-call = {count}; '
                   f'{row["matched"]} matched, {row["unresolved"]} unresolved')
    edges = Counter((r['region'], by_id[p]['region'], r['dependency'])
                    for r in report['operations'] for p in r['producers'])
    for (consumer, producer, kind), count in sorted(edges.items()):
        out.append(f'    {consumer or "<outside regions>"} waits on completion published by '
                   f'{producer or "<outside regions>"}: {count} observations ({kind})')
    out += ['  note: ' + w for w in report['warnings']]
    if report.get('pendingCalls'):
        out.append(f'  {len(report["pendingCalls"])} unfinished synchronization calls retained; '
                   'their objects have no resolved producer mappings.')
    if report.get('unattributedOperations'):
        out.append('  outside application regions (aggregated): '+', '.join(
            f'{api}: {count}' for api, count in sorted(report['unattributedOperations'].items())))
    return out
