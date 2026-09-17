"""Audit a GXVM Wan trace and summarize modeled kernel work and stream gaps."""
import argparse
from collections import Counter, defaultdict
import json
import gzip
from pathlib import Path
import re

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--report', type=Path, required=True)
p.add_argument('--trace', type=Path, required=True)
p.add_argument('--log', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--export-trace', type=Path, help='Measured interval only, with CPU phase ranges; .gz supported')
a = p.parse_args()
r = json.loads(a.report.read_text())
trace = json.loads(a.trace.read_text())
assert r['clock'] == 'gxvm_time_ns'
assert trace.get('gxClock') == 'host_before_adoption_logical_after_adoption', 'Mixed/unknown trace clock'
start, end = r['start_ns']/1000, r['end_ns']/1000
events = [e for e in trace['traceEvents'] if e.get('ph') == 'X'
          and start <= e.get('args', {}).get('create_ts_us', -1) <= end]
predicted = [e for e in events if e['name'] in ('kernel_predict', 'cublas_predict')]
assert predicted
assert all(e['args']['prediction_status'] == 'hit' for e in predicted)
assert all(start <= e['ts'] <= e['ts'] + e['dur'] <= end + .001 for e in events), 'Invalid time range'
assert all(e['args']['create_ts_us'] <= e['ts'] + .001 for e in events), 'Task starts before enqueue'
summaries = re.findall(r'^GX_PREDICT_SUMMARY .+$', a.log.read_text(), re.M)
assert len(summaries) == 1
counters = dict(re.findall(r'(\w+)=(\S+)', summaries[0]))
assert int(counters['misses']) == int(counters['errors']) == 0
assert int(counters['hits']) == int(counters['virtual_wait_calls']) == len(predicted)
total = sum(e['args']['predicted_duration_ns'] for e in predicted)
assert total == int(counters['predicted_latency_ns'])
streams = defaultdict(list)
for e in events:
    streams[e['tid']].append(e)
stream_rows = []
for stream, es in streams.items():
    cursor = start
    gaps = []
    occupied = 0
    for e in sorted(es, key=lambda e: e['ts']):
        assert e['ts'] >= cursor - .001, 'Overlapping tasks within a serial stream'
        if e['ts'] > cursor:
            gaps.append(dict(start_ns=round(cursor*1000), end_ns=round(e['ts']*1000),
                             seconds=(e['ts']-cursor)/1e6))
        occupied += e['dur']
        cursor = e['ts'] + e['dur']
    if cursor < end:
        gaps.append(dict(start_ns=round(cursor*1000), end_ns=round(end*1000), seconds=(end-cursor)/1e6))
    stream_rows.append(dict(stream=stream, task_seconds=occupied/1e6,
                            gap_seconds=sum(g['seconds'] for g in gaps),
                            largest_gaps=sorted(gaps, key=lambda g: -g['seconds'])[:20]))
costs, counts = Counter(), Counter()
for e in predicted:
    args = e['args']
    key = args.get('kernel_name', args.get('operation'))
    costs[key] += args['predicted_duration_ns']
    counts[key] += 1
phases = defaultdict(lambda: dict(calls=0, host_submission_virtual_seconds=0., predicted_kernel_seconds=0.))
for e in r['phase_events']:
    entry = phases[e['name']]
    entry['calls'] += 1
    entry['host_submission_virtual_seconds'] += (e['end_ns']-e['start_ns'])/1e9
    entry['predicted_kernel_seconds'] += sum(
        k['args']['predicted_duration_ns']/1e9 for k in predicted
        if e['start_ns']/1000 <= k['args']['create_ts_us'] < e['end_ns']/1000)
result = dict(elapsed_virtual_seconds=r['elapsed_seconds'], launches=len(predicted),
              predicted_kernel_seconds=total/1e9, counters=counters, streams=stream_rows,
              phases=dict(phases), kernels=[dict(name=k, calls=counts[k], predicted_seconds=v/1e9)
                                           for k,v in costs.most_common()],
              limitations=['Task durations include epoch rounding and simulator bookkeeping.',
                           'Stream gaps are not a direct measurement of application CPU cost.',
                           'Phase submission ranges can overlap queued GPU work.'])
a.output.write_text(json.dumps(result, indent=2)+'\n')
if a.export_trace:
    visible = [e for e in trace['traceEvents'] if e.get('ph') == 'M'] + events
    visible += [dict(name='process_name', ph='M', pid=1, tid=1,
                     args=dict(name='Wan CPU submission phases'))]
    visible += [dict(name=e['name'], cat='cpu_submission', ph='X', pid=1, tid=1,
                     ts=e['start_ns']/1000, dur=(e['end_ns']-e['start_ns'])/1000)
                for e in r['phase_events']]
    output = dict(traceEvents=visible, displayTimeUnit='ms', gxClock='gxvm_logical_ns')
    opener = gzip.open if a.export_trace.suffix == '.gz' else open
    with opener(a.export_trace, 'wt') as stream:
        json.dump(output, stream, separators=(',', ':'))
print(json.dumps({k:v for k,v in result.items() if k not in ('kernels','limitations')}, indent=2))
