#!/usr/bin/env python3
"""Persist real drperf feedback for isolated annotation/optimization trials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import derive
import runner


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def analyze(raw, case):
    rs = runner.load_runs(str(raw))
    warnings = runner.validity(rs)
    keys, slots = runner.blocks_of_set(rs)
    slots = runner.demangle_slots(slots)
    recs = runner.load_traces_all(rs)
    vecs, triggers, names, nested, dropped = derive.inclusive_vectors(keys, case, recs)
    regimes = derive.derive(vecs, slots, split=False)
    rows = []
    for state in sorted(vecs):
        instructions = sum(count for slot, count in vecs[state].items()
                           if not derive.is_runtime(slots.get(slot, ('?', '?', None))[:2]))
        row = {'state': dict(zip(names, state)), 'calls': triggers[state],
               'instructions_per_call': instructions}
        if regimes:
            irr = regimes[0].irr.get(state, 0.0)
            row.update(unexplained_instructions_per_call=irr,
                       unexplained_share=irr / instructions if instructions else 0.0)
        rows.append(row)
    needed = max(derive.MIN_VALUES, len(names) + 2)
    sufficient = bool(regimes) and len(rows) >= needed
    worst = max((r['unexplained_share'] for r in rows), default=None) if regimes else None
    reasons = list(warnings)
    if not rows: reasons.append('target marker has no counted state points')
    if not sufficient: reasons.append(f'insufficient state points: {len(rows)}; need {needed}')
    if dropped: reasons.append(f'{dropped} target calls were dropped')
    if nested: reasons.append('nested marked regions exclude work from target')
    if worst is not None and worst > 0.05: reasons.append('unexplained share exceeds 5% at an observed state')
    metrics = {'case': case, 'validity_warnings': warnings, 'pcv_names': names,
               'distinct_states': len(rows), 'required_states': needed,
               'calls': sum(triggers.values()), 'dropped_calls': dropped,
               'nested_calls_per_call': nested, 'states': rows,
               'max_unexplained_share': worst, 'threshold': 0.05,
               'sufficient_points': sufficient, 'gate_pass': not reasons,
               'gate_reasons': reasons, 'automatic_regime_splitting': False,
               'instruction_scope': 'target own work, excluding configured runtime waiting modules; marker overhead included'}
    lines = []
    if regimes:
        r = regimes[0]
        metrics['formula'] = {'coefficients': dict(zip(names, r.a)), 'constant': r.c,
                              'dependent_columns': sorted(r.dependent)}
        lines.append(case + ' = ' + ' + '.join([f'{a:.8g}*{n}' for n,a in zip(names,r.a)] + [f'{r.c:.8g}']) + ' + unexplained')
        for (module, symbol), cost in sorted(r.by_sym_irr.items(), key=lambda x: -x[1])[:20]:
            lines.append(f'  unexplained {cost:.8g} instr/call: {symbol} [{module}]')
        for name, attribution in zip(names, r.by_sym_a):
            for (module, symbol), cost in sorted(attribution.items(), key=lambda x: -abs(x[1]))[:8]:
                lines.append(f'  {name} coefficient {cost:.8g}: {symbol} [{module}]')
    lines.extend('gate: ' + reason for reason in reasons)
    return metrics, '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    r = sub.add_parser('run')
    r.add_argument('--case', required=True)
    r.add_argument('--workspace', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--timeout', type=float, default=120)
    r.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command: p.error('provide a workload command after --')
    workspace, out = a.workspace.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = {str(f.relative_to(workspace)): hashlib.sha256(f.read_bytes()).hexdigest()
               for f in workspace.rglob('*.py')
               if '_runtime' not in f.parts and '__pycache__' not in f.parts and not f.is_relative_to(out)}
    write(out / 'invocation.json', {'case': a.case, 'command': command, 'workspace': str(workspace),
                                  'timeout_seconds': a.timeout, 'source_hashes': sources,
                                  'environment': {k: os.environ[k] for k in ('HF_HOME','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','PYTHONHASHSEED') if k in os.environ}})
    previous = Path.cwd()
    start = time.monotonic()
    try:
        os.chdir(workspace)
        rc, log, files = runner.run(command, str(out / 'raw'), a.timeout)
    finally:
        os.chdir(previous)
    (out / 'output.txt').write_text(log)
    metrics = {'case': a.case, 'gate_pass': False, 'gate_reasons': ['no drperf files']}
    feedback = ''
    if files:
        try:
            metrics, feedback = analyze(out / 'raw', a.case)
        except Exception as exc:
            metrics['gate_reasons'] = [f'analysis failed: {type(exc).__name__}: {exc}']
    if rc:
        metrics['gate_pass'] = False
        metrics['gate_reasons'].append(f'workload return code {rc}')
    metrics.update(returncode=rc, instrumented_wall_seconds=time.monotonic()-start, raw_files=files)
    write(out / 'metrics.json', metrics)
    (out / 'feedback.txt').write_text(feedback)
    print(json.dumps({'out': str(out), 'returncode': rc, 'gate_pass': metrics['gate_pass'],
                      'max_unexplained_share': metrics.get('max_unexplained_share'),
                      'gate_reasons': metrics['gate_reasons']}))
    return 0 if rc == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
