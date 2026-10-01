#!/usr/bin/env python3
"""Build and run the same ordinary regions, with and without a producer delay."""
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
import explorer
import runner
import waits

out = ROOT / 'out/waits'
out.mkdir(parents=True, exist_ok=True)
program = out / 'demo'
subprocess.run(['gcc', '-O2', '-pthread', str(Path(__file__).with_name('demo.c')),
                '-I'+str(ROOT/'perfmark'), '-L'+str(ROOT/'build'), '-lperfmark',
                '-Wl,-rpath,'+str(ROOT/'build'), '-o', str(program)], check=True)
for label, delay in [('baseline', '0'), ('delayed', '100')]:
    # This example owns these raw outputs; do not pool earlier executions.
    for previous in (out/label).glob('run.*.json*'):
        previous.unlink()
    with patch.dict(os.environ, {'DRPERF_WAITS': '1', 'DRPERF_FOLLOW_THREADS': '0',
                                'DRPERF_WAIT_DELAY_REGION': 'decode', 'DRPERF_WAIT_DELAY_MS': delay}):
        rc, log, _ = runner.run([str(program)], str(out/label), timeout=60)
    if rc:
        raise RuntimeError(log)
    model = explorer.build_model(out/label, ROOT, ['examples/waits/demo.c'], discover=False)
    if model['validity']['errors'] or model['validity']['traceErrors']:
        raise RuntimeError(model['validity'])
    explorer.write_model(model, out/(label+'.drperf.json'))
    print(label, log.strip())
    print('\n'.join(waits.lines(model['waits'])))
    ops = [e for e in model['waits']['operations'] if e['api']=='sem_wait']
    print('  semaphore ordering:', [e.get('ordering', e['reason']) for e in ops])
    print('  semaphore syscall attempts:', sum(e['potentialSyscalls'] for e in ops))
