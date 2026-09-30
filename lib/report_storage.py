"""Keep raw synchronization evidence out of the portable viewer report.

The JSON retains all fitted costs, region traces, summaries, checked results,
and exact endpoints needed by the graph. Full wait evidence is an adjacent,
checksummed sidecar, loaded explicitly for rechecking. Operations reference
their original events rather than serializing those event fields twice.
"""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

FORMAT = 'drperf.wait-evidence.v1'


def require_inline_waits(model):
    if (model.get('waits') or {}).get('evidence'):
        raise ValueError('Full synchronization evidence is external. Load the report with '
                         'explorer.load_model(path, wait_evidence=True) before rechecking.')


def externalize_waits(model, destination):
    """Return a display report without mutating the full in-memory model."""
    capture = model.get('waits')
    if not capture:
        return model
    require_inline_waits(model)
    events, operations = capture.get('events', []), capture.get('operations', [])
    if not events and not operations:
        return model
    destination = Path(destination)
    by_id = {event['id']: event for event in events}
    if len(by_id) != len(events):
        raise ValueError('Duplicate synchronization record ID')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.waits.tmp',
                                         delete=False) as raw:
            temporary = Path(raw.name)
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw,
                               compresslevel=1, mtime=0) as zipped:
                def emit(record):
                    zipped.write((json.dumps(record, separators=(',', ':'),
                                             allow_nan=False) + '\n').encode('utf-8'))
                for event in events:
                    emit(['event', event])
                for operation in operations:
                    event = by_id.get(operation['id'])
                    if event is not None and event.keys() <= operation.keys():
                        delta = {key: value for key, value in operation.items()
                                 if key not in event or value != event[key]}
                        emit(['operation', operation['id'], delta])
                    else:
                        emit(['operation', operation])
        with temporary.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        # Content-addressed publication keeps the old report/evidence valid if
        # replacement of the new report fails or a reader still has it open.
        sidecar = destination.with_name(destination.name + '.waits.' + digest[:16] + '.jsonl.gz')
        temporary.replace(sidecar)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    # Retain exact invocation endpoints for graph expansion and declared edges.
    # Other native observations remain available as summaries AND full evidence.
    visible_operations = [op for op in operations if op.get('region') and op.get('producers')]
    keep = {op['id'] for op in visible_operations}
    keep.update(producer for op in visible_operations for producer in op['producers'])
    keep.update(event['id'] for event in events if event.get('kind', '').startswith('declared_'))
    keep.update(event['id'] for event in capture.get('pendingCalls', []))
    visible_events = [event for event in events if event['id'] in keep]
    return dict(model, waits=dict(capture, events=visible_events, operations=visible_operations,
        evidence={'format': FORMAT, 'path': sidecar.name, 'sha256': digest,
                  'bytes': sidecar.stat().st_size,
                  'eventCount': len(events), 'operationCount': len(operations),
                  'inlineEventCount': len(visible_events),
                  'inlineOperationCount': len(visible_operations),
                  'scope': 'Inline records support display only. Load the complete sidecar '
                           'before checking event order, missing waits, or native provenance.'}))


def load_model(path, wait_evidence=False):
    path = Path(path)
    model = json.loads(path.read_text())
    reference = (model.get('waits') or {}).get('evidence')
    if not wait_evidence or not reference:
        return model
    name = reference.get('path')
    if (reference.get('format') != FORMAT or not isinstance(name, str)
            or Path(name).name != name or name in ('', '.', '..')):
        raise ValueError('Invalid synchronization evidence reference')
    sidecar = path.parent / name
    try:
        with sidecar.open('rb') as raw:
            digest = hashlib.file_digest(raw, 'sha256').hexdigest()
            if raw.seek(0, 2) != reference['bytes'] or digest != reference['sha256']:
                raise ValueError('Synchronization evidence size/hash mismatch: ' + str(sidecar))
            raw.seek(0)
            events, operations, by_id = [], [], {}
            with gzip.GzipFile(fileobj=raw, mode='rb') as zipped:
                for line in zipped:
                    row = json.loads(line)
                    if row[0] == 'event' and len(row) == 2:
                        event = row[1]
                        if event['id'] in by_id:
                            raise ValueError('Duplicate synchronization record ID')
                        events.append(event)
                        by_id[event['id']] = event
                    elif row[0] == 'operation' and len(row) == 3:
                        if row[1] not in by_id:
                            raise ValueError('Synchronization operation has no source event')
                        operations.append(dict(by_id[row[1]], **row[2]))
                    elif row[0] == 'operation' and len(row) == 2:
                        operations.append(row[1])
                    else:
                        raise ValueError('Invalid synchronization evidence record')
    except FileNotFoundError as error:
        raise ValueError('Full synchronization evidence is required for rechecking: ' + str(sidecar)) from error
    if len(events) != reference['eventCount'] or len(operations) != reference['operationCount']:
        raise ValueError('Synchronization evidence record count mismatch')
    model['waits'].update(events=events, operations=operations)
    del model['waits']['evidence']
    return model
