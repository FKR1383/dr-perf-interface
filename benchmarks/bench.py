#!/usr/bin/env python3
"""Supervisor CLI for paired PCV-discovery experiments."""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import pstats
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DRPERF = ROOT.parent


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2)+'\n')


def snapshot(workspace):
    return {str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in workspace.rglob('*') if p.is_file() and
            (p.suffix in ('.py', '.c', '.h', '.rs', '.so')) and 'measurements' not in p.parts}


def submit(workspace, claims_path):
    config = read(workspace/'session.json')
    answer = read(claims_path)
    claims = answer.get('claims') if isinstance(answer,dict) else None
    if not isinstance(claims,list):
        raise ValueError('submission must contain a claims list')
    ids=[]
    for claim in claims:
        if not isinstance(claim,dict) or not all(isinstance(claim.get(k),str) and claim[k].strip()
                   for k in ('id','region','expression','evidence')):
            raise ValueError('every claim needs id, region, expression and evidence strings')
        ids.append(claim['id'])
    if len(ids)!=len(set(ids)):
        raise ValueError('claim IDs must be unique')
    history = workspace/'measurements'
    history.mkdir(exist_ok=True)
    with (history/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rounds=sorted(history.glob('round-*'))
        if any(read(p/'result.json')['status']=='running' for p in rounds):
            raise ValueError('finish the measurement round before submitting its answer')
        number=len(rounds)
        submissions=history/'submissions'
        submissions.mkdir(exist_ok=True)
        target=submissions/f'round-{number:02d}.json'
        if target.exists():
            raise ValueError('this round already has a recorded submission')
        if number and not (submissions/f'round-{number-1:02d}.json').exists():
            raise ValueError('record a submission at round 0 and after every measurement; missing earlier answer')
        write(target,{'case':config['case'],'condition':config['condition'],
                      'track':config.get('track','discovery'),
                      'round':number,'claims':claims,'source_hashes':snapshot(workspace)})
    print(target)
    return 0


def measure(workspace, mode, plan_path, hypothesis_path):
    config = read(workspace/'session.json')
    if mode == 'drperf' and config['condition'] != 'drperf':
        raise ValueError('the timing condition has no drperf feedback')
    points = read(plan_path)
    if not isinstance(points, list) or not 1 <= len(points) <= config['points_per_round']:
        raise ValueError(f"plan must contain 1..{config['points_per_round']} input configurations")
    for point in points:
        if not isinstance(point, dict) or any(not isinstance(k,str) or not isinstance(v,(str,int,float)) for k,v in point.items()):
            raise ValueError('each point must be a mapping of workload arguments to scalar values')
        envelope = config.get('input_envelope')
        if config.get('track') == 'small-to-large' and not envelope:
            raise ValueError('small-to-large sessions require an explicit input envelope')
        if envelope:
            if set(point) != set(envelope):
                raise ValueError('input envelope requires exactly these explicit arguments: ' + ', '.join(envelope))
            for key, bounds in envelope.items():
                if type(point[key]) is not int or not bounds['min'] <= point[key] <= bounds['max']:
                    raise ValueError(f'input {key} is outside the small-input envelope')
    hypothesis = read(hypothesis_path)
    if not isinstance(hypothesis,dict) or not isinstance(hypothesis.get('claims'),list):
        raise ValueError('hypothesis must contain a claims list')
    history = workspace/'measurements'
    history.mkdir(exist_ok=True)
    # Reserve before execution, including failed/timed-out rounds. Serialize
    # reservations to prevent concurrent calls bypassing the budget.
    with (history/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        used = len(list(history.glob('round-*')))
        if used >= config['round_budget']:
            raise ValueError('measurement budget exhausted')
        if any(read(p/'result.json')['status']=='running' for p in history.glob('round-*')):
            raise ValueError('another measurement round is still running')
        out = history/f'round-{used+1:02d}'
        out.mkdir()
        write(out/'result.json',{'status':'running'})
    write(out/'hypothesis.json', hypothesis)
    write(out/'plan.json', points)
    write(out/'source-hashes.json', snapshot(workspace))
    result = {'round':used+1, 'mode':mode, 'condition':config['condition'],
              'track':config.get('track','discovery'),
              'case':config['case'], 'status':'running', 'points':[]}
    write(out/'result.json',result)
    env = dict(os.environ, **config['env'])
    for key in ('DRPERF','DRPERF_LATE','DYNAMORIO_OPTIONS','LD_PRELOAD','PERFMARK_CALIBRATE'):
        env.pop(key,None)
    env['PYTHONPATH'] = os.pathsep.join([str(workspace),env.get('PYTHONPATH',''),str(DRPERF/'perfmark/python')])
    env['PERFMARK_LIB'] = str(DRPERF/'build/libperfmark.so')
    sys.path.insert(0,str(DRPERF/'lib'))
    import runner
    for i, point in enumerate(points):
        point_dir = out/f'point-{i:02d}'
        point_dir.mkdir()
        command = [config['python']]
        profile = point_dir/'profile.pstats'
        if mode == 'timing':
            command += ['-m','cProfile','-o',str(profile)]
        command += [str(workspace/config['workload'])] + [f'{k}={v}' for k,v in point.items()]
        started = time.monotonic()
        if mode == 'drperf':
            # runner.run inherits os.environ, so restore it even on failures.
            old_env, old_cwd = dict(os.environ), Path.cwd()
            try:
                os.environ.clear()
                os.environ.update(env)
                os.chdir(workspace)
                rc, log, files = runner.run(command,str(point_dir/'raw'),config['process_timeout_seconds'])
            finally:
                os.environ.clear()
                os.environ.update(old_env)
                os.chdir(old_cwd)
            warnings = []
            if files:
                rs = runner.load_runs(str(point_dir/'raw'))
                warnings = runner.validity(rs)
            else:
                warnings = ['No drperf records: add a region annotation before requesting feedback.']
        else:
            try:
                proc = subprocess.run(command,cwd=workspace,env=env,capture_output=True,text=True,
                                      timeout=config['process_timeout_seconds'])
                rc,log = proc.returncode,proc.stdout+proc.stderr
            except subprocess.TimeoutExpired as exc:
                rc = -1
                log = (exc.stdout or b'').decode(errors='replace') + (exc.stderr or b'').decode(errors='replace')+'\nTIMEOUT\n'
            warnings = []
            if profile.exists():
                stream = io.StringIO()
                pstats.Stats(str(profile),stream=stream).strip_dirs().sort_stats('cumulative').print_stats(60)
                (point_dir/'profile.txt').write_text(stream.getvalue())
        (point_dir/'output.txt').write_text(log)
        result['points'].append({'input':point,'returncode':rc,'wall_seconds':time.monotonic()-started,'warnings':warnings})
        write(out/'result.json',result)
    if mode == 'drperf' and all(p['returncode']==0 and not p['warnings'] for p in result['points']):
        merged = out/'merged'
        merged.mkdir()
        for i,point in enumerate(points):
            raw = out/f'point-{i:02d}'/'raw'
            for file in raw.iterdir():
                shutil.copy2(file,merged/f'{i:02d}-{file.name}')
        rs = runner.load_runs(str(merged))
        keys,slots = runner.blocks_of_set(rs)
        if keys:
            cli = runpy.run_path(str(DRPERF/'bin/drperf'))
            lines = cli['cost_lines'](rs,keys,runner.demangle_slots(slots),runner.load_traces_all(rs))
            (out/'feedback.txt').write_text('\n'.join(lines)+'\n')
        else:
            result['error'] = 'No counted regions in traces.'
    result['status'] = 'ok' if not result.get('error') and all(p['returncode']==0 and not p['warnings'] for p in result['points']) else 'invalid'
    write(out/'result.json', result)
    print(json.dumps({'output':str(out),'status':result['status']},indent=2))
    return 0 if result['status']=='ok' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('list')
    p = sub.add_parser('prepare')
    p.add_argument('case'); p.add_argument('destination',type=Path)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--condition',choices=['timing','drperf'],required=True)
    p.add_argument('--track',choices=['discovery','small-to-large'],default='discovery')
    p = sub.add_parser('measure')
    p.add_argument('workspace',type=Path)
    p.add_argument('--mode',choices=['timing','drperf'],required=True)
    p.add_argument('--plan',type=Path)
    p.add_argument('--hypothesis',type=Path)
    p = sub.add_parser('submit')
    p.add_argument('workspace',type=Path)
    p.add_argument('--claims',type=Path)
    args = parser.parse_args()
    try:
        if args.cmd == 'list':
            from adapters.prepare import SPECS
            for case in read(ROOT/'catalog.json')['cases']:
                info = read(ROOT/'cases'/case/'case.json')
                print(f"{case:14} {'pilot adapter' if case in SPECS else 'reference only':16} {info['title']}")
        elif args.cmd == 'prepare':
            from adapters.prepare import SPECS, prepare
            if args.case not in SPECS:
                raise ValueError('this case has historical evidence but no reviewed neutral adapter yet')
            prepare(args.case,args.destination.resolve(),args.archive.resolve(),DRPERF,args.condition,args.track)
            print(args.destination.resolve())
        elif args.cmd == 'submit':
            workspace=args.workspace.resolve()
            return submit(workspace,args.claims or workspace/'hypothesis.json')
        else:
            workspace = args.workspace.resolve()
            return measure(workspace,args.mode,args.plan or workspace/'plan.json',
                           args.hypothesis or workspace/'hypothesis.json')
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2,f'benchmark: {exc}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
