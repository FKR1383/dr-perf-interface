#!/usr/bin/env python3
"""Run passive-event examples, plan delays from baseline gaps, then falsify bugs."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'lib'))
import event_model
import explorer
import runner

out = ROOT/'out/waits/events'
out.mkdir(parents=True, exist_ok=True)
program = out/'demo'
subprocess.run(['gcc', '-O2', '-pthread', str(Path(__file__).with_name('events.c')),
                '-I'+str(ROOT/'perfmark'), '-L'+str(ROOT/'build'), '-lperfmark',
                '-Wl,-rpath,'+str(ROOT/'build'), '-o', str(program)], check=True)


def run(mode, label, target='', delay=0):
    raw = out/(mode+'-'+label)
    for f in raw.glob('run.*.json*'): f.unlink()
    with patch.dict(os.environ, {'DRPERF_WAITS':'1', 'DRPERF_FOLLOW_THREADS':'0',
          'DRPERF_WAIT_DELAY_KIND':'event', 'DRPERF_WAIT_DELAY_REGION':target,
          'DRPERF_WAIT_DELAY_MS':str(delay)}):
        rc, log, _ = runner.run([str(program), mode], str(raw), timeout=30)
    if rc: raise RuntimeError(log)
    model = explorer.build_model(raw, ROOT, ['examples/waits/events.c'], discover=False)
    assert not model['validity']['errors'] and not model['validity']['traceErrors'], model['validity']
    explorer.write_model(model, out/(mode+'-'+label+'.drperf.json'))
    result = model.get('eventModel')
    assert result, 'Event hooks were not observed'
    return result


results = {}
for mode in ['correct', 'conditional', 'chain', 'missing-wait', 'wrong-pair', 'omitted']:
    baseline = run(mode, 'baseline')
    if mode == 'omitted':
        # The closed semaphore lifetime resolves its native publisher, but does
        # not manufacture an application-level waited declaration.
        assert not baseline['edges'] and baseline['nativeResolved'] >= 1, baseline
        results[mode] = {'baseline':baseline}
        print(mode, 'native synchronization retained; no declared edge invented', flush=True)
        continue
    assert not baseline['violations'] and not baseline['unverified'], (mode, baseline)
    target = 'C' if mode in ['chain', 'wrong-pair'] else 'B'
    plan = next(p for p in event_model.probe_plan(baseline) if p['region']==target)
    perturbed = run(mode, 'probe', target, plan['delayMs'])
    expected_violation = mode in ['missing-wait', 'wrong-pair']
    assert bool(perturbed['violations']) == expected_violation, (mode, plan, perturbed)
    assert perturbed['probe']
    if mode == 'conditional':
        interface = next(i for i in baseline['interfaces'] if i['region']=='A')
        assert (interface['present'], interface['absent']) == (2,2)
        assert interface['countFormula']['coefficients']==['1']
        assert interface['countFormula']['constant']=='0'
    results[mode] = {'baseline':baseline, 'plan':plan, 'probe':perturbed}
    print(mode, 'baseline='+baseline['status'], 'delay='+str(plan['delayMs'])+'ms',
          'probe='+perturbed['status'], flush=True)
(out/'results.json').write_text(json.dumps(results, indent=2)+'\n')
print(out/'results.json')
