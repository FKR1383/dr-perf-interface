#!/usr/bin/env python3
"""Compare collected snapshots with pinned Git objects in local upstream clones."""
import argparse, datetime, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--checkouts-json',type=Path,help='Optional mapping from repository URLs to local clone paths');p.add_argument('--out',type=Path,default=ROOT/'benchmarks/growth/upstream-verification.json');a=p.parse_args()
configured=json.loads(a.checkouts_json.read_text()) if a.checkouts_json else {}
seen=set();rows=[]
for group in ('compiler-frontends','general-libraries','language-tools','native-libraries'):
    for path in sorted((ROOT/'benchmarks/regions'/group/'cases').glob('*/case.json')):
        data=json.loads(path.read_text());source=data['source'];snapshot=(path.parent/source['snapshot']).resolve();key=(source['repository'],source['revision'],source['path'])
        if key in seen:continue
        seen.add(key)
        project=snapshot.parts[snapshot.parts.index('upstream')+1]
        defaults={'compiler-frontends':Path('/tmp/drperf-cf/llvm'),'general-libraries':Path('/tmp')/('drperf-gl-'+project),'language-tools':Path('/tmp/ignored_runtime')/project,'native-libraries':Path('/tmp/drperf-growth-rapidjson')}
        checkout=Path(configured.get(source['repository'],defaults[group]))
        result=subprocess.run(['git','-C',str(checkout),'show',source['revision']+':'+source['path']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        upstream=hashlib.sha256(result.stdout).hexdigest() if result.returncode==0 else None
        actual=hashlib.sha256(snapshot.read_bytes()).hexdigest()
        rows.append({'group':group,'project':project,'repository':source['repository'],'revision':source['revision'],'source_path':source['path'],'manifest_sha256':source['sha256'],'snapshot_sha256':actual,'git_object_sha256':upstream,'matches_git_object':upstream==actual==source['sha256'],'error':result.stderr.decode() if result.returncode else None})
result={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'distinct_source_files':len(rows),'mismatches':[row for row in rows if not row['matches_git_object']],'files':rows}
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'checked':len(rows),'mismatches':len(result['mismatches'])}))
raise SystemExit(bool(result['mismatches']))
