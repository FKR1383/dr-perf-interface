#!/usr/bin/env python3
"""Collect concrete fixture witnesses for executed pinned compiler functions.

This is native source coverage for case selection, not drperf performance data.
The exported LCOV function records retain source coordinates from the marked
build worktree; consumers must map them back to pristine coordinates.
"""
import argparse, concurrent.futures, functools, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--bin',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);p.add_argument('--ids',nargs='*');a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
runner=a.out.resolve()/'run_case.py';runner.write_bytes((ROOT/'benchmarks/regions/compiler-frontends/test-support/run_case.py').read_bytes())
profdata='/usr/lib/llvm-18/bin/llvm-profdata';cov='/usr/lib/llvm-18/bin/llvm-cov'

@functools.lru_cache(maxsize=None)
def original_lines(relative):
    pristine=subprocess.check_output(['git','-C',str(a.source),'show','HEAD:'+relative]).decode().splitlines()
    marked=(a.source/relative).read_text().splitlines();mapping={};old=0
    for number,line in enumerate(marked,1):
        if line.strip()=='#include "drperf_bench_region.h"' or re.fullmatch(r'\s*DRPERF_BENCH_REGION\("cf-\d+"\);\s*',line):continue
        assert pristine[old]==line, (relative,number)
        old+=1;mapping[number]=old
    assert old==len(pristine),relative
    return mapping

def run(path):
    raw=(path.parent/'tests/spec.json').read_bytes();spec=json.loads(raw);cid=spec['case'];binary=a.bin.resolve()/spec['compiler']
    with tempfile.TemporaryDirectory(prefix='drperf-cf-coverage-') as tmp:
        tmp=Path(tmp);frozen=tmp/'spec.json';frozen.write_bytes(raw)
        env=dict(os.environ,LLVM_PROFILE_FILE=str(tmp/'profile-%p.profraw'));env.pop('DRPERF_ENTRY_LOG',None);env['DRPERF_CC']=str(binary);env['PATH']=str(a.bin.resolve())+os.pathsep+env.get('PATH','')
        result=subprocess.run([sys.executable,str(runner),str(frozen)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
        row={'id':cid,'spec_sha256':hashlib.sha256(raw).hexdigest(),'returncode':result.returncode,'output':result.stdout[-4000:],'functions':[]}
        profiles=sorted(tmp.glob('*.profraw'))
        if result.returncode==0 and profiles:
            merged=tmp/'merged.profdata';subprocess.run([profdata,'merge','-sparse',*[str(p) for p in profiles],'-o',str(merged)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            # LCOV retains per-function counts in a substantially smaller form
            # than detailed JSON regions; header functions are not case targets.
            export=subprocess.run([cov,'export',str(binary),'-instr-profile='+str(merged),'-format=lcov','-skip-branches','-skip-expansions','-ignore-filename-regex=(/include/|/utils/|/third-party/|[.]h$|[.]inc$)'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120)
            file=None;starts={}
            for line in export.stdout.splitlines():
                if line.startswith('SF:'):
                    candidate=Path(line[3:]);file=str(candidate.relative_to(a.source.resolve())) if candidate.is_relative_to(a.source.resolve()) and candidate.suffix=='.cpp' else None;starts={}
                elif file and line.startswith('FN:'):
                    location,name=line[3:].split(',',1);starts[name]=int(location)
                elif file and line.startswith('FNDA:'):
                    count,name=line[5:].split(',',1)
                    if int(count)>0 and name in starts:row['functions'].append({'source':file,'marked_line':starts[name],'original_line':original_lines(file).get(starts[name]),'name':name,'count':int(count)})
        (a.out/(cid+'.json')).write_text(json.dumps(row,indent=2)+'\n')
        print(cid,result.returncode,len(row['functions']),flush=True)
        return {'id':cid,'returncode':result.returncode,'function_count':len(row['functions']),'spec_sha256':row['spec_sha256']}
paths=sorted((ROOT/'benchmarks/regions/compiler-frontends/cases').glob('*/case.json'))
if a.ids:paths=[p for p in paths if p.parent.name in a.ids]
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:results=list(pool.map(run,paths))
(a.out/'summary.json').write_text(json.dumps({'kind':'source-coverage fixture witnesses, not performance evidence','runner_sha256':hashlib.sha256(runner.read_bytes()).hexdigest(),'cases':len(results),'results':results},indent=2)+'\n')
