"""Exclude identifiable marker blocks before fitting, without estimated subtraction.

Current clients exclude marker modules during execution, including the dynamic
extent of native event helpers. Legacy captures still use exact block removal.
Ordinary Python region wrappers and caller-side argument preparation remain measured. Work in
explicit PCV regions is kept separate by the client's exclusive counters and
omitted from application interfaces by the exporter.
"""
from collections import Counter, defaultdict
from pathlib import Path

CALIB = "_perfmark_calibration"


def is_marker(symbol):
    module, name = symbol[:2]
    module = Path(module).name
    return (module == 'libperfmark.so' or module.startswith('libperfmark.so.') or
            module == '_perfmark.so' or module.startswith('_perfmark.') and module.endswith('.so') or
            name in ('perfmark_begin', 'perfmark_begin_v', 'perfmark_end', 'perfmark_state', 'perfmark_event_publish', 'perfmark_event_waited'))


def _run(key):
    return key[0] if isinstance(key, tuple) else 0


def adjust(keys, slots, records, trace_errors=()):
    """Return corrected keys and per-region/state accounting; keep raw intact."""
    schemas = {}
    for row in keys.values():
        if not row.get('overflow') and row['count']:
            schemas.setdefault(row['region'], tuple(n for n, _ in row['states']))
    expected, children = Counter(), Counter()
    for key, row in keys.items():
        if not row.get('overflow'):
            expected[(_run(key), row['region'], tuple(v for _, v in row['states']))] += row['count']
    active = defaultdict(list)
    valid = not trace_errors
    for record in sorted(records, key=lambda r: (r.get('run', 0), r.get('pid', 0), r['seq'])):
        run, name = record.get('run', 0), record['region']
        stack = active[(run, record.get('pid', 0), record['tid'])]
        while stack and stack[-1][1] < record['seq']:
            stack.pop()
        if stack and record['seq_end'] >= stack[-1][1]:
            valid = False
        names = schemas.get(name)
        try:
            state = tuple(int(record.get('state', {})[n]) for n in names) if names is not None else None
        except (KeyError, TypeError, ValueError):
            state = None
        identity = (run, name, state)
        if stack:
            children[stack[-1][0]] += 1
        stack.append((identity, record['seq_end']))
    # Aggregate identical state buckets while retaining the raw input for audit.
    grouped = {}
    for key, row in keys.items():
        identity = (_run(key), row['region'], tuple(row['states']), bool(row.get('overflow')))
        if identity not in grouped:
            grouped[identity] = (key, dict(row, vec=Counter(), count=0))
        merged = grouped[identity][1]
        merged['vec'].update(row['vec'])
        merged['count'] += row['count']
    corrected, totals = {}, defaultdict(lambda: defaultdict(float))
    for key, row in grouped.values():
        run = _run(key)
        state = tuple(v for _, v in row['states'])
        identity = (run, row['region'], state)
        count = row['count']
        result = dict(row)
        vector = {b: c for b, c in row['vec'].items() if not is_marker(slots.get(b, ('?', '?')))}
        removed = sum(row['vec'].values()) - sum(vector.values())
        summary = totals[(row['region'], state)]
        summary['calls'] += count
        summary['exactBlocks'] += removed
        summary['directChildCalls'] += (children[identity] * count / expected[identity]
                                         if valid and expected[identity] else 0)
        result['vec'] = {b: c for b, c in vector.items() if c}
        corrected[key] = result
    return corrected, {key: dict(value) for key, value in totals.items()}


def metadata(region, states, accounting):
    points = []
    for (name, state), row in sorted(accounting.items()):
        if name != region or not row['calls']:
            continue
        n = row['calls']
        points.append({'state': list(state), 'exactBlocks': row['exactBlocks']/n,
                       'directChildCalls': row.get('directChildCalls', 0)/n,
                       'calls': n})
    return {'method': 'marker-module exclusion only',
            'scope': 'marker modules excluded exactly; current clients also exclude native event helpers and their callees; no calibration subtraction; ordinary Python region wrappers and caller-side preparation remain unless explicitly excluded',
            'points': points}
