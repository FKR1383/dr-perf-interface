#!/usr/bin/env python3
"""Overlay all compiler entry markers in a dedicated, pinned coverage worktree.

Independent baseline patches stay unchanged. Simultaneous markers are only for
native reachability checks, never for performance cost measurements.
"""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REV='87f0227cb60147a26a1eeb4fb06e3b505e9c7261'
p=argparse.ArgumentParser();p.add_argument('checkout',type=Path);p.add_argument('--record',type=Path,required=True);a=p.parse_args()
checkout=a.checkout.resolve()
assert checkout!=ROOT and (checkout/'.git').exists(), 'use a separate compiler worktree'
assert subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()==REV
files=collections.defaultdict(list)
for manifest in sorted((ROOT/'benchmarks/regions/compiler-frontends/cases').glob('*/case.json')):
    data=json.loads(manifest.read_text());assert data['source']['revision']==REV
    rel=Path(data['source']['path']);assert not rel.is_absolute() and '..' not in rel.parts
    old_line=0;insertions=[]
    for line in (manifest.parent/'region.patch').read_text().splitlines(True):
        hunk=re.match(r'^@@ -(\d+)',line)
        if hunk:old_line=int(hunk[1])
        elif line.startswith(('+++','---')):continue
        elif line.startswith('+'):
            if f'DRPERF_BENCH_REGION("{data["id"]}")' in line:
                insertions.append((old_line-1,line[1:]))
        elif line.startswith((' ','-')):old_line+=1
    assert len(insertions)==1,(manifest,insertions)
    files[rel.as_posix()].append({'id':data['id'],'insertion':insertions[0],'pristine_sha256':data['source']['sha256']})
previous=json.loads(a.record.read_text())['files'] if a.record.exists() else {}
record={}
for rel in sorted(set(previous)|set(files)):
    raw=subprocess.check_output(['git','-C',str(checkout),'show',REV+':'+rel])
    rows=files.get(rel,[])
    for row in rows:assert hashlib.sha256(raw).hexdigest()==row['pristine_sha256']
    lines=raw.decode().splitlines(True)
    for offset,line in sorted((r['insertion'] for r in rows),reverse=True):lines.insert(offset,line)
    if rows:
        offset=next(i for i,line in enumerate(lines) if line.startswith('#include'))
        lines.insert(offset,'#include "drperf_bench_region.h"\n')
    marked=''.join(lines).encode();target=checkout/rel
    if target.read_bytes()!=marked:target.write_bytes(marked)
    if rows:record[rel]={'ids':[r['id'] for r in rows],'sha256':hashlib.sha256(marked).hexdigest()}
a.record.parent.mkdir(parents=True,exist_ok=True)
a.record.write_text(json.dumps({'revision':REV,'checkout':str(checkout),'purpose':'simultaneous native entry observation only; not cost accounting','cases':sum(len(v) for v in files.values()),'files':record},indent=2)+'\n')
print(f'Prepared {sum(len(v) for v in files.values())} markers in {len(files)} compiler source files')
