#!/usr/bin/env python3
"""Rerun a seeded sample of verified general-library cases in isolated copies.

Optional --runtimes-json maps each project to {"source": checkout_or_runtime,
"python": interpreter}. Defaults describe the collection host; reproduce those
environments using the general-libraries README or supply your own paths.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
GROUP=ROOT/'benchmarks/regions/general-libraries'
loader=importlib.util.spec_from_file_location('collection',ROOT/'benchmarks/regions/collect.py')
collection=importlib.util.module_from_spec(loader);loader.loader.exec_module(collection)
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtimes-json',type=Path);p.add_argument('--seed',type=int,default=20260915)
p.add_argument('--per-project',type=int,default=2);p.add_argument('--jobs',type=int,default=3)
p.add_argument('--out',type=Path,default=ROOT/'benchmarks/growth/general-libraries-independent.json')
a=p.parse_args();rng=random.Random(a.seed)
config=json.loads(a.runtimes_json.read_text()) if a.runtimes_json else {}
by_project={}
for manifest in sorted((GROUP/'cases').glob('*/case.json')):
    data=json.loads(manifest.read_text())
    if data['tests']['validation']['status']!='region-verified':continue
    snapshot=Path(data['source']['snapshot']);project=snapshot.parts[snapshot.parts.index('upstream')+1]
    by_project.setdefault(project,[]).append(manifest)
selected=[]
for project,manifests in sorted(by_project.items()):
    selected.extend((project,m) for m in rng.sample(manifests,min(a.per_project,len(manifests))))
if len(by_project)!=9:raise SystemExit('Require verified candidates in all nine projects before sampling')

def run(item):
    project,manifest=item;data=json.loads(manifest.read_text());cid=data['id']
    env_name=project if project in {'numpy','pandas','urllib3','jsonschema'} else 'misc'
    python='/usr/bin/python3' if project=='networkx' else f'/tmp/drperf-gl-venv-{env_name}/bin/python'
    source=f'/tmp/drperf-gl-venv-{project}/lib/python3.12/site-packages' if project in {'numpy','pandas'} else '/tmp/drperf-gl-'+project
    runtime=config.get(project,{'source':source,'python':python})
    with tempfile.TemporaryDirectory(prefix='drperf-gl-independent-') as tmp:
        work=Path(tmp)/'runtime';work.mkdir()
        subprocess.run(['cp','-al',str(Path(runtime['source']).resolve())+'/.',str(work)],check=True)
        target=work/data['source']['path']
        # Copies share unmodified files. Detach the target before writing it.
        if target.exists():target.unlink()
        collection.apply(manifest,data,work)
        target_sha=hashlib.sha256(target.read_bytes()).hexdigest()
        command=[runtime['python'],str(ROOT/'benchmarks/regions/collect.py'),'test',cid,
                 '--python',runtime['python'],'--source-root',str(work)]
        try:
            result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,timeout=120)
            row={'returncode':result.returncode,'output':(result.stdout+result.stderr)[-5000:]}
        except subprocess.TimeoutExpired:
            row={'returncode':None,'output':'Timeout after 120 seconds'}
        row.update({'id':cid,'project':project,'source':data['source'],'region':data['region'],
                    'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    'patch_sha256':hashlib.sha256((manifest.parent/'region.patch').read_bytes()).hexdigest(),
                    'test_sha256':hashlib.sha256((manifest.parent/'tests/test_case.py').read_bytes()).hexdigest(),
                    'marked_source_sha256':target_sha,'python':runtime['python']})
        return row
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:results=list(pool.map(run,selected))
report={'scope':'Independent rerun of seeded samples from the verified cohort; no performance measurement',
        'seed':a.seed,'sampled_per_project':a.per_project,'cases':len(results),
        'passed':sum(r['returncode']==0 for r in results),'results':results}
a.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
raise SystemExit(any(r['returncode']!=0 for r in results))
