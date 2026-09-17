#!/usr/bin/env python3
"""Run each bounded compiler fixture separately and require its target marker.

Uses an instrumented pinned build prepared with prepare_compiler_probe.py. The
observer reports native region entry only, not cost or an affine interface.
"""
import argparse, collections, concurrent.futures, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--bin',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--jobs',type=int,default=8);p.add_argument('--case',action='append',help='Check only named cases (repeatable)');a=p.parse_args()
record=json.loads(a.record.read_text());a.out.mkdir(parents=True,exist_ok=True)
runner=ROOT/'benchmarks/regions/compiler-frontends/test-support/run_case.py'
runner_bytes=runner.read_bytes()
runner=a.out.resolve()/'run_case.py'
runner.write_bytes(runner_bytes)

def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

paths=sorted((ROOT/'benchmarks/regions/compiler-frontends/cases').glob('*/case.json'))
if a.case:
    unknown=set(a.case)-{m.parent.name for m in paths}
    if unknown:raise SystemExit(f'Unknown cases: {sorted(unknown)}')
    paths=[m for m in paths if m.parent.name in a.case]
binary_names=sorted({json.loads((m.parent/'tests/spec.json').read_text())['compiler'] for m in paths})
binary_hashes={name:sha256(a.bin/name) for name in binary_names if (a.bin/name).is_file()}
cache=a.bin.resolve().parent/'CMakeCache.txt'
build_evidence={'binaries_sha256':binary_hashes,
                'instrumented_record_sha256':sha256(a.record),
                'cmake_cache_sha256':sha256(cache) if cache.is_file() else None,
                'marker_helper_sha256':sha256(ROOT/'benchmarks/regions/support/drperf_bench_region.h'),
                'observer_source_sha256':sha256(Path(__file__).with_name('compiler_observer.cpp'))}

def run(manifest):
    data=json.loads(manifest.read_text());cid=data['id'];source=data['source']['path']
    assert cid in record['files'][source]['ids'], 'target missing from instrumented build record'
    target=Path(record['checkout'])/source
    assert hashlib.sha256(target.read_bytes()).hexdigest()==record['files'][source]['sha256'], 'instrumented source changed'
    spec_path=manifest.parent/'tests/spec.json';spec_bytes=spec_path.read_bytes();spec=json.loads(spec_bytes)
    binary=a.bin.resolve()/spec['compiler'];rows=[]
    if not binary.is_file():return {'id':cid,'status':'missing-binary','binary':str(binary),'rows':[]}
    for item in spec.get('fixtures',[{'size':1,'source':spec['fixture']}]):
        with tempfile.TemporaryDirectory(prefix='drperf-cf-entry-') as tmp:
            tmp=Path(tmp);one=dict(spec);one['fixtures']=[item];small=tmp/'spec.json';small.write_text(json.dumps(one));trace=tmp/'entries.txt'
            env=dict(os.environ,DRPERF_CC=str(binary),DRPERF_ENTRY_LOG=str(trace));env['PATH']=str(a.bin.resolve())+os.pathsep+env.get('PATH','')
            try:
                result=subprocess.run([sys.executable,str(runner),str(small)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
                entries=trace.read_text().splitlines() if trace.exists() else []
                rows.append({'size':item['size'],'returncode':result.returncode,'target_entries':entries.count(cid),'observed_region_count':len(set(entries)),'observed_entries':dict(collections.Counter(entries)),'output':result.stdout[-6000:]})
            except subprocess.TimeoutExpired:
                rows.append({'size':item['size'],'returncode':None,'target_entries':0,'error':'timeout120seconds'})
    ok=all(r['returncode']==0 and r['target_entries']>0 for r in rows)
    test_hashes={name:sha256(manifest.parent/name) for name in data['tests']['files']}
    test_hashes.update({r['destination']:sha256(manifest.parent/r['source']) for r in data['tests'].get('resources',[])})
    result={'id':cid,'status':'region-verified' if ok else 'failed',
            'source':data['source'],'region':data['region'],
            'patch_sha256':sha256(manifest.parent/'region.patch'),
            'test_assets_sha256':test_hashes,
            'spec_sha256':hashlib.sha256(spec_bytes).hexdigest(),
            'binary':str(binary),'binary_sha256':binary_hashes[spec['compiler']],'rows':rows}
    (a.out/(cid+'.json')).write_text(json.dumps(result,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
    results=list(pool.map(run,paths))
summary={'kind':'native target entry and fixture assertions; simultaneous marks not valid for cost accounting','revision':record['revision'],'runner_sha256':hashlib.sha256(runner_bytes).hexdigest(),'cases':len(results),'region_verified':sum(r['status']=='region-verified' for r in results),'missing_binary':sum(r['status']=='missing-binary' for r in results),'failed':sum(r['status']=='failed' for r in results),'results':results}
summary['build_evidence']=build_evidence
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='results'}))
