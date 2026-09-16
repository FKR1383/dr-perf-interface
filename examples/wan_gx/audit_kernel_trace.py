#!/usr/bin/env python3
"""Compare a GX launch trace with the measured native launch inventory.

Checks observable launch metadata, not tensor values or equivalence of arbitrary
kernel arguments. A positive result is a prerequisite for timing, not proof of
numerical correctness. Use the raw profiler DB with observed_launches retained.
Replay requires the explicit logical-clock tracing patch.
"""
import argparse
from collections import Counter, defaultdict
import json
import hashlib
from pathlib import Path
import sqlite3


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native-db', type=Path, required=True)
    ap.add_argument('--native-report', type=Path, required=True)
    ap.add_argument('--emu-report', type=Path, required=True)
    ap.add_argument('--trace', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--allow-source-change', action='append', default=[],
                    help='Explicitly reviewed application file allowed to differ from native profiling')
    a = ap.parse_args()
    native = json.loads(a.native_report.read_text())
    emu = json.loads(a.emu_report.read_text())
    trace = json.loads(a.trace.read_text())
    if emu['clock'] == 'gxvm_time_ns':
        if trace.get('gxClock') != 'host_before_adoption_logical_after_adoption':
            ap.error('Replay requires the explicit logical-clock trace patch.')
        start, end = emu['start_ns']/1000, emu['end_ns']/1000
    elif emu['clock'] == 'host_perf_counter_ns':
        start, end = emu['start_perf_counter_ns']/1000, emu['end_perf_counter_ns']/1000
    else:
        ap.error('Unrecognized report clock')
    config_fields = ('config', 'prompt', 'warmup_steps', 'convolution_backend', 'packages',
                     'cudnn_version', 'cudnn_policy')
    config_differences = [k for k in config_fields if native.get(k) != emu.get(k)]
    source_changes = {name: dict(native=native['source_sha256'].get(name),
                                emulated=emu['source_sha256'].get(name))
                      for name in native['source_sha256'].keys() | emu['source_sha256'].keys()
                      if native['source_sha256'].get(name) != emu['source_sha256'].get(name)}
    if set(source_changes) - set(a.allow_source_change):
        config_differences.append('source_sha256')
    db = sqlite3.connect(f'file:{a.native_db.resolve()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    rows = list(db.execute('SELECT * FROM kernel_signatures'))
    skipped = [dict(row) for row in db.execute('SELECT * FROM skipped_launches')]
    counts = dict(db.execute('SELECT kernel_id, SUM(count) FROM observed_launches GROUP BY kernel_id'))
    samples = dict(db.execute('SELECT kernel_id, COUNT(*) FROM kernel_samples WHERE warmup=0 '
                              'AND gate_timed_out=0 AND duration_ns>0 GROUP BY kernel_id'))
    by_key = defaultdict(list)
    native_counts = Counter()
    for row in rows:
        key = (row['name'], *(row[f'{axis}_{dim}'] for axis in ('grid','block') for dim in 'xyz'))
        by_key[key].append(row)
        native_counts[key] += counts.get(row['id'], 0)
    events = trace['traceEvents']
    emu_counts, missing, ambiguous, bad_metadata, bad_samples = (Counter() for _ in range(5))
    sequences = defaultdict(hashlib.sha256)
    for event in events:
        if event.get('ph') != 'X' or event.get('name') not in ('kernel_predict', 'cublas_predict'):
            continue
        args = event['args']
        # Select by enqueue time; stream workers may begin processing later.
        if not start <= args['create_ts_us'] <= end:
            continue
        name = args.get('kernel_name', args.get('operation'))
        key = (name, *(args[axis][dim] for axis in ('grid','block') for dim in 'xyz'))
        metadata = (('param_hash', args['param_hash']) if event['name'] == 'cublas_predict'
                    else ('shared_mem_bytes', args['shared_mem_bytes']))
        sequences[str(args['stream'])].update(json.dumps((key, metadata), separators=(',', ':')).encode()+b'\n')
        emu_counts[key] += 1
        candidates = by_key.get(key, [])
        if not candidates:
            missing[key] += 1
            continue
        # GX's current predictor projects onto this key. Distinct native full
        # signatures sharing it need explicit resolution before using its time.
        if len(candidates) != 1:
            ambiguous[key] += 1
            continue
        row = candidates[0]
        if event['name'] == 'cublas_predict':
            if args['param_hash'] != row['param_hash'] % (1 << 64):
                bad_metadata[key] += 1
        elif args['shared_mem_bytes'] != row['dynamic_shared_bytes']:
            bad_metadata[key] += 1
        if not samples.get(row['id']):
            bad_samples[key] += 1
    differences = {key: (native_counts[key], emu_counts[key])
                   for key in native_counts.keys() | emu_counts.keys()
                   if native_counts[key] != emu_counts[key]}
    def entries(counter):
        return [dict(name=key[0], grid=list(key[1:4]), block=list(key[4:7]), count=value)
                for key, value in sorted(counter.items())]
    result = dict(
        observable_inventory_matches=not (config_differences or missing or ambiguous or bad_metadata
                                           or bad_samples or differences or skipped) and bool(emu_counts),
        limitations=['Does not compare tensor values or arbitrary kernel arguments.',
                     'Regular kernel parameter hashes and cluster dimensions are absent from GX trace.'],
        config_differences=config_differences, skipped_native_launches=skipped,
        source_changes=source_changes, allowed_source_changes=a.allow_source_change,
        emulated_stream_sequence_sha256={stream: digest.hexdigest() for stream, digest in sequences.items()},
        native_launches=sum(native_counts.values()), emu_launches=sum(emu_counts.values()),
        missing=entries(missing), ambiguous=entries(ambiguous),
        mismatched_metadata=entries(bad_metadata), without_usable_samples=entries(bad_samples),
        count_differences=entries(differences),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('limitations','count_differences')}, indent=2))
    raise SystemExit(0 if result['observable_inventory_matches'] else 2)


if __name__ == '__main__':
    main()
