"""Check declared synchronization indicators against every captured invocation.

No inference from elapsed time. The producer is the completion-publication site,
not necessarily the site that submitted every preceding item of device work.
"""
import ast
from collections import Counter, defaultdict
import operator

import composition
import waits

# Supported observations in the existing wait collector. Queries deliberately
# remain unsupported until they have a compatible, tested capture path.
APIS = {
    'sem_wait', 'sem_timedwait', 'sem_clockwait', 'pthread_mutex_lock',
    'pthread_mutex_timedlock', 'pthread_cond_wait', 'pthread_cond_timedwait',
    'pthread_join', 'recv', 'recvfrom', 'recvmsg', 'cudaEventSynchronize',
    'cudaStreamSynchronize', 'cudaDeviceSynchronize', 'cudaStreamWaitEvent',
}
BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
       ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}


class Indicator:
    def __init__(self, source, names):
        if not isinstance(source, str) or len(source) > 2048:
            raise ValueError('Indicator must be a short expression string')
        self.tree = ast.parse(source, mode='eval').body
        allowed = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.BoolOp,
                   ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
                   ast.BinOp, ast.Compare, *BIN, *CMP)
        nodes = list(ast.walk(self.tree))
        if len(nodes) > 128:
            raise ValueError('Indicator is too complex')
        for node in nodes:
            if not isinstance(node, allowed):
                raise ValueError('Unsupported indicator syntax: ' + type(node).__name__)
            if isinstance(node, ast.Name) and node.id not in names:
                raise ValueError('Unknown entry PCV: ' + node.id)
            if isinstance(node, ast.Constant) and type(node.value) not in (int, bool):
                raise ValueError('Indicator constants must be integers or booleans')

    def __call__(self, values):
        def ev(n):
            if isinstance(n, ast.Name):
                result = composition._integer(values[n.id])
            elif isinstance(n, ast.Constant):
                result = n.value
            elif isinstance(n, ast.BoolOp):
                result = (all(bool(ev(x)) for x in n.values) if isinstance(n.op, ast.And)
                          else any(bool(ev(x)) for x in n.values))
            elif isinstance(n, ast.UnaryOp):
                value = ev(n.operand)
                result = not value if isinstance(n.op, ast.Not) else (-value if isinstance(n.op, ast.USub) else value)
            elif isinstance(n, ast.BinOp):
                result = BIN[type(n.op)](ev(n.left), ev(n.right))
            else:
                left = ev(n.left)
                for op, right in zip(n.ops, n.comparators):
                    value = ev(right)
                    if not CMP[type(op)](left, value):
                        return False
                    left = value
                result = True
            if isinstance(result, int) and result.bit_length() > 4096:
                raise ValueError('Indicator arithmetic exceeded the integer budget')
            return result
        try:
            result = ev(self.tree)
        except ArithmeticError as error:
            raise ValueError('Indicator arithmetic failed: ' + str(error)) from error
        if result not in (0, 1):
            raise ValueError('Indicator must evaluate to 0 or 1, not a count')
        return bool(result)


def invocation(record, trace=False):
    return record['group'], str(record['thread'] if trace else record['tid']), record['seq' if trace else 'regionSeq']


def check(model, declaration):
    if declaration.get('version') != 1 or not isinstance(declaration.get('claims'), list):
        raise ValueError('Expected version 1 and a claims array')
    regions = {r['id']: r for r in model['regions']}
    claims, selectors, ids = [], set(), set()
    for claim in declaration['claims']:
        if set(claim) - {'id', 'region', 'api', 'indicator', 'producer'}:
            raise ValueError('Unsupported claim field; selectors must not hide observations')
        region, api, identity = claim['region'], claim['api'], claim['id']
        if region not in regions:
            raise ValueError('Unknown region: ' + region)
        if api not in APIS:
            raise ValueError('API not supported by this collector: ' + api)
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError('Claim IDs must be distinct nonempty strings')
        if (region, api) in selectors:
            raise ValueError('Use one indicator per region/API; combine conditions with or')
        ids.add(identity); selectors.add((region, api))
        producer = claim.get('producer')
        if producer is not None and (not isinstance(producer, str) or not producer):
            raise ValueError('Producer must be a region name or null')
        claims.append((claim, Indicator(claim['indicator'], regions[region]['states'])))
    report = {'status': 'unverified', 'claims': [], 'unexplained': [], 'coverage': {},
              'contract': 'Exclusive region operations; indicators predict presence, not blocking. '
                          'Zero-operation invocations are checked. Multiplicity is fitted separately. '
                          'Producer means observed completion-publication region. Only captured executions '
                          'and supported APIs are covered; queries and custom predicates are not covered.'}
    from report_storage import require_inline_waits
    require_inline_waits(model)
    capture = model.get('waits') or {}
    if (capture.get('status') != 'observed' or capture.get('warnings')
            or not model.get('trace', {}).get('complete')
            or model.get('validity', {}).get('errors') or model.get('validity', {}).get('traceErrors')):
        report['reason'] = 'Complete, valid trace and synchronization capture required; absence cannot be checked.'
        return report
    traces = model['trace']['events']
    composition._forest(regions, traces)  # Do not mistake missing invocations for absent waits.
    by_call = {invocation(t, True): t for t in traces}
    events = capture.get('events', [])
    counts_by_group = Counter(e['group'] for e in events)
    for index, run in enumerate(model.get('provenance', {}).get('runs', [])):
        measurement = run.get('measurement', {})
        if 'wait_records' in measurement:
            group = f"{index}:{measurement.get('pid', 0)}"
            if measurement.get('wait_dropped') or counts_by_group[group] != measurement['wait_records']:
                report['reason'] = 'Synchronization record count differs from capture metadata.'
                return report
    event_ids = [e['id'] for e in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError('Duplicate synchronization record ID')
    if any(not e.get('returned') or not e.get('end') for e in events):
        report['reason'] = 'Unfinished synchronization records; cannot validate absence.'
        return report
    canonical = []
    for event in events:
        event = dict(event)
        parent = by_call.get(invocation(event))
        if event.get('regionSeq') and not parent and event.get('region') in regions:
            raise ValueError('Synchronization references a missing region invocation')
        event['region'] = parent['region'] if parent else ''
        canonical.append(event)
    by_id = {e['id']: e for e in canonical}
    # Derive object-generation links afresh, rather than trusting supplied producer labels.
    operations = waits.analyze(canonical)
    observed = defaultdict(list)
    for op in operations:
        observed[invocation(op), op['api']].append(op)
    consumed = set()
    for claim, indicator in claims:
        name, api = claim['region'], claim['api']
        calls = [t for t in traces if t['region'] == name]
        row = {'id': claim['id'], 'region': name, 'api': api,
               'indicator': claim['indicator'], 'producer': claim.get('producer'),
               'invocations': len(calls), 'present': 0, 'absent': 0,
               'observedOperations': 0, 'unexpectedPresence': 0, 'unexpectedAbsence': 0,
               'producerMismatches': 0, 'producerUnverified': 0, 'failedOperations': 0,
               'counterexamples': [], 'status': 'unverified'}
        active_states, counts = [], []
        def example(kind, call, ops, **extra):
            if len(row['counterexamples']) < 8:
                row['counterexamples'].append({'kind': kind, 'invocation': list(invocation(call, True)),
                    'state': call['values'], 'observations': [o['id'] for o in ops], **extra})
        for call in calls:
            ops = observed[invocation(call, True), api]
            predicted = indicator(call['values'])
            actual = bool(ops)
            row['present' if actual else 'absent'] += 1
            row['observedOperations'] += len(ops)
            if predicted != actual:
                key = 'unexpectedPresence' if actual else 'unexpectedAbsence'
                row[key] += 1; example(key, call, ops, indicator=int(predicted))
            if actual:
                active_states.append([composition._integer(call['values'][n]) for n in regions[name]['states']])
                counts.append(len(ops))
            for op in ops:
                verified = predicted
                if not waits.succeeded(op):
                    row['failedOperations'] += 1; verified = False
                    example('failedOperation', call, [op])
                producers = [by_id[p]['region'] for p in op['producers']]
                if not claim.get('producer') or not producers or op['dependency'] == 'observed-stream-prefix':
                    row['producerUnverified'] += 1; verified = False
                elif any(p != claim['producer'] for p in producers):
                    row['producerMismatches'] += 1; verified = False
                    example('producerMismatch', call, [op], observedProducers=producers)
                if verified:
                    consumed.add(op['id'])
        row['indicatorStatus'] = ('invalid' if row['unexpectedPresence'] or row['unexpectedAbsence']
                                  else 'verified-observed' if calls else 'unverified')
        row['producerStatus'] = ('invalid' if row['producerMismatches'] else
                                'unverified' if row['producerUnverified'] or row['failedOperations'] or not row['observedOperations']
                                else 'verified-observed')
        row['status'] = ('invalid' if 'invalid' in (row['indicatorStatus'], row['producerStatus']) else
                         'verified-observed' if row['indicatorStatus'] == row['producerStatus'] == 'verified-observed'
                         else 'unverified')
        row['multiplicity'] = composition.affine(active_states, counts, regions[name]['states'])
        row['multiplicityStates'] = regions[name]['states']
        row['branchCoverage'] = 'both outcomes' if row['present'] and row['absent'] else 'only present' if row['present'] else 'only absent'
        report['claims'].append(row)
    residual = defaultdict(list)
    for op in operations:
        if op['region'] and op['id'] not in consumed:
            residual[op['region'], op['api']].append(op)
    for (region, api), ops in sorted(residual.items()):
        targets = sorted({by_id[p]['region'] or '?' for o in ops for p in o['producers']})
        report['unexplained'].append({'region': region, 'api': api, 'operations': len(ops),
            'observedProducers': targets, 'term': 'unexplained(Wait[' + ('|'.join(targets) if targets else '?') + '])',
            'examples': [o['id'] for o in ops[:3]]})
    report['coverage'] = {'regionInvocations': len(traces), 'recordedOperations': len(operations),
        'regionOperations': sum(bool(o['region']) for o in operations),
        'explainedOperations': len(consumed), 'unexplainedOperations': sum(r['operations'] for r in report['unexplained']),
        'outsideRegionOperations': sum(not o['region'] for o in operations),
        'outsideRegionAggregates': capture.get('unattributedOperations', {}),
        'captureCoverage': capture.get('coverage', 'Selected APIs only'),
        'delayProbe': bool(capture.get('probe'))}
    report['status'] = ('invalid' if any(r['status'] == 'invalid' for r in report['claims']) else
                        'incomplete' if residual or any(r['status'] != 'verified-observed' for r in report['claims']) else
                        'verified-observed')
    return report


def lines(report):
    out = ['Wait indicator check: ' + report['status']]
    if report.get('reason'):
        return out + [report['reason']]
    for r in report['claims']:
        target = r['producer'] or '?'
        multiplier = composition.affine_text(r['multiplicity'], r['multiplicityStates']) if r['multiplicity'] else '?'
        out += [f"  {r['id']}: {r['status']} | I_{{{r['indicator']}}} * ({multiplier}) * Wait[{target}]",
                f"    {r['present']} present, {r['absent']} absent; indicator {r['indicatorStatus']}; producer {r['producerStatus']}"]
        for e in r['counterexamples']:
            out.append(f"    {e['kind']}: invocation={e['invocation']} PCVs={e['state']}")
    c = report['coverage']
    out.append(f"  Explained {c['explainedOperations']}/{c['regionOperations']} in-region synchronization operations.")
    for r in report['unexplained']:
        out.append(f"    {r['region']} {r['api']}: {r['operations']} * {r['term']}")
    out.append(report['contract'])
    return out
