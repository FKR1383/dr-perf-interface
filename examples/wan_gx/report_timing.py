"""Package a checked, fixed-kernel CPU optimization comparison (no hardware claim)."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
for name in ('baseline-timing', 'optimized-timing', 'baseline-drperf', 'optimized-drperf'):
    p.add_argument('--'+name, type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--controllers', type=Path, default=Path('/home/ubuntu/GX/NEX/build/experiments'))
a = p.parse_args()

def read(path):
    return json.loads(path.read_text())

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

records = {}
for name in ('baseline', 'optimized'):
    timing = getattr(a, name+'_timing')
    drperf = getattr(a, name+'_drperf')
    report = read(timing/'wan/report.json')
    inventory = read(timing/'inventory-audit.json')
    timeline = read(timing/'timing-audit.json')
    counts = read(drperf/'drperf-summary.json')
    marked = read(drperf/'wan/report.json')
    run_id = Path(report['environment']['GXVM_EPOCH_PATH']).parts[-3]
    controllers = list(a.controllers.glob('*-'+run_id))
    assert len(controllers) == 1, run_id
    controller = controllers[0]
    completion = read(controller/'result.json')
    assert completion['passed'] and not completion['cleanup_errors']
    runtime = read(controller/'runtime.json')
    assert inventory['observable_inventory_matches']
    assert report['config']['sampling_steps'] == 50 and report['config']['frame_num'] == 81
    assert report['shape'] == [3,81,480,832]
    assert not counts['validity']
    assert len(counts['counters']) == 1
    counters = counts['counters'][0]
    drperf_id = Path(counters['trace_file']).parts[3]
    drperf_controllers = list(a.controllers.glob('*-'+drperf_id))
    assert len(drperf_controllers) == 1, drperf_id
    drperf_completion = read(drperf_controllers[0]/'result.json')
    assert drperf_completion['passed'] and not drperf_completion['cleanup_errors']
    assert counters['excluded_cuda_module'] == 'gx_cuda.so'
    assert counters['excluded_cuda_exports'] and counters['excluded_cuda_calls']
    assert not counters['follow_unmarked_threads'] and not counters['depth_overflows']
    assert all(v['gx_module_instructions'] == 0 and v['dropped'] == 0 for v in counts['regions'].values())
    for key in ('config','prompt','warmup_steps','source_sha256','packages','cudnn_version','cudnn_policy'):
        assert report[key] == marked[key], (name,key)
    for key in ('GX_PREDICT_DB','GX_CUDA_CONTEXT_LIMITS','GX_CUDA_DEVICE_ATTRIBUTES','GX_REAL_CUDNN'):
        assert report['environment'][key] == marked['environment'][key], (name,key)
    paths = [timing/'wan/report.json', timing/'inventory-audit.json', timing/'timing-audit.json',
             drperf/'drperf-summary.json', drperf/'wan/report.json']
    paths += sorted((drperf/'drperf/raw').glob('*'))
    paths += sorted((timing/'kernel_profile_gx').glob('*.json'))
    records[name] = dict(workload=report, inventory=inventory, timing=timeline, drperf=counts,
                         controller_completion=completion, runtime=runtime,
                         drperf_controller_completion=drperf_completion,
                         raw_sha256={str(path): digest(path) for path in paths if path.is_file()})

left, right = records['baseline'], records['optimized']
for key in ('config','prompt','warmup_steps','packages','cudnn_version','cudnn_policy'):
    assert left['workload'][key] == right['workload'][key], key
ignored = {'GXVM_EPOCH_PATH'}
le = {k:v for k,v in left['workload']['environment'].items() if k not in ignored}
re = {k:v for k,v in right['workload']['environment'].items() if k not in ignored}
assert le == re, 'Timing policy or staged inputs changed'
assert left['runtime']['dynamorio'] == right['runtime']['dynamorio'], 'Staged GXVM runtime changed'
assert left['inventory']['emulated_stream_sequence_sha256'] == right['inventory']['emulated_stream_sequence_sha256']
assert left['timing']['predicted_kernel_seconds'] == right['timing']['predicted_kernel_seconds']
assert set(left['drperf']['regions']) == set(right['drperf']['regions'])
old, new = left['timing']['elapsed_virtual_seconds'], right['timing']['elapsed_virtual_seconds']
before, after = (records[name]['drperf']['total_marked_own_instructions'] for name in ('baseline','optimized'))
result = dict(records=records, comparison=dict(
    baseline_virtual_seconds=old, optimized_virtual_seconds=new,
    virtual_reduction_percent=100*(1-new/old), baseline_marked_instructions=before,
    optimized_marked_instructions=after, marked_instruction_reduction_percent=100*(1-after/before)),
    limitations=['One paired simulation, not a statistical hardware speedup measurement.',
                 'GX skips GPU arithmetic; full GPU output equivalence is not measured.',
                 'CPU replay includes sampled costs and qualified fallbacks; unresolved samples remain.',
                 'drperf counts marked caller-thread work; most fixed-shape regions have insufficient states for an affine fit.',
                 'Stream task durations include epoch rounding and simulator bookkeeping.'])
validation_logs = list(a.optimized_drperf.glob('gx-*.log'))
assert len(validation_logs) == 1
validation = validation_logs[0].read_text()
assert 'PASS: 12 nonzero transformer comparisons' in validation
assert 'Validation torch: '+right['workload']['packages']['torch'] in validation
result['cpu_validation'] = dict(log=str(validation_logs[0]), sha256=digest(validation_logs[0]),
                               checks='12 exact nonzero CPU outputs and operation sequences; CUDA autocast policy')
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result['comparison'], indent=2))
