#!/usr/bin/env python3
import pathlib, subprocess, tempfile, shutil, sys, json, hashlib, platform, importlib.metadata
project, first, last, executable=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
base=pathlib.Path(__file__).resolve().parents[3]
source=pathlib.Path(sys.argv[5]) if len(sys.argv)>5 else pathlib.Path('/tmp/drperf-gl-'+project)
passed=[]; failed=[]; receipts=[]
PACKAGE_NAMES=["numpy","scipy","pandas","networkx","requests","urllib3","jsonschema","attrs","packaging","pathspec","numba","pyOpenSSL","cryptography"]
def package_versions():
    code="import importlib.metadata,json; names="+repr(PACKAGE_NAMES)+"; print(json.dumps({n:importlib.metadata.version(n) for n in names if next(iter([importlib.metadata.version(n)]),None)}))"
    try: return json.loads(subprocess.check_output([executable,"-c",code],text=True,stderr=subprocess.DEVNULL))
    except Exception:
        versions={}
        for name in PACKAGE_NAMES:
            try: versions[name]=subprocess.check_output([executable,"-c",f"import importlib.metadata; print(importlib.metadata.version({name!r}))"],text=True,stderr=subprocess.DEVNULL).strip()
            except Exception: pass
        return versions
env_packages=package_versions()
for number in range(first,last+1):
    case_id=f'gl-{number:03d}'
    work=pathlib.Path(tempfile.mkdtemp(prefix=f'gl-{project}-'))
    subprocess.run(['cp','-al',str(source)+'/.',str(work)],check=True,stdout=subprocess.DEVNULL)
    case_dir=base/'benchmarks/regions/general-libraries/cases'/case_id
    manifest=json.loads((case_dir/'case.json').read_text())
    pristine=(case_dir/manifest['source']['snapshot']).resolve()
    target=work/manifest['source']['path'];target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): target.unlink()  # break cp -al hardlink before overlay
    shutil.copy2(pristine,target)
    patch=case_dir/'region.patch'
    applied=subprocess.run(['git','-C',work,'apply',patch],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if applied.returncode:
        applied=subprocess.run(['git','-C',work,'apply',patch],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if applied.returncode:
            failed.append(case_id+': installed source differs from pristine patch context')
            shutil.rmtree(work)
            continue
    try:
        command=[executable,str(base/'benchmarks/regions/collect.py'),'test',case_id,'--python',executable,'--source-root',str(work)]
        result=subprocess.run(command,cwd=base,text=True,capture_output=True,timeout=30)
    except subprocess.TimeoutExpired:
        failed.append(case_id+': timeout'); receipts.append({"id":case_id,"command":command,"returncode":None,"timeout":30,"marker_hits":{},"python":platform.python_version()})
    else:
        marker={}
        for line in result.stdout.splitlines():
            try:
                item=json.loads(line)
                if "marker_hits" in item: marker=item["marker_hits"]
            except json.JSONDecodeError: pass
        receipts.append({"id":case_id,"command":command,"returncode":result.returncode,"marker_hits":marker,"python":subprocess.check_output([executable,'--version'],text=True,stderr=subprocess.STDOUT).strip(),"source_revision":manifest["source"]["revision"],"source_path":manifest["source"]["path"],"source_sha256":manifest["source"]["sha256"],"patch_sha256":hashlib.sha256((case_dir/'region.patch').read_bytes()).hexdigest(),"test_sha256":hashlib.sha256((case_dir/'tests/test_case.py').read_bytes()).hexdigest(),"marked_source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"stdout":result.stdout[-2000:],"stderr":result.stderr[-2000:]})
        if result.returncode==0 and marker.get(case_id,0)>0: passed.append(case_id)
        else:
            lines=[x for x in result.stderr.splitlines() if x.strip() and not x.startswith('/tmp/drperf-case')]
            failed.append(case_id+': '+(lines[-1][:180] if lines else 'failed'))
    shutil.rmtree(work)
print(project,'PASS',len(passed),','.join(passed))
print(project,'FAIL',len(failed))
print(*failed,sep='\n')
receipt_dir=base/'benchmarks/regions/general-libraries/validation-executions';receipt_dir.mkdir(exist_ok=True)
receipt_path=receipt_dir/f'{project}.json'
prior={r['id']:r for r in json.loads(receipt_path.read_text()).get('results',[])} if receipt_path.exists() else {}
prior.update({r['id']:r for r in receipts})
receipt_path.write_text(json.dumps({"project":project,"source_root":str(source),"executable":executable,"environment":{"python":subprocess.check_output([executable,"--version"],text=True,stderr=subprocess.STDOUT).strip(),"packages":env_packages},"results":[prior[k] for k in sorted(prior)]},indent=2)+'\n')
