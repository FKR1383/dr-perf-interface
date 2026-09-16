"""Download pinned official weights once, with LFS digest verification."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/wan-gx'
MODEL = 'Wan-AI/Wan2.1-T2V-1.3B'
REV = '37ec512624d61f7aa208f7ea8140a131f93afc9a'
manifest = json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{MODEL}/revision/{REV}?blobs=true'))
assert manifest['sha'] == REV
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'model-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def fetch(f):
    name=f['rfilename']; path=OUT/'checkpoint'/name
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.stat().st_size == f['size']:
        if 'lfs' in f:
            with path.open('rb') as cached:
                assert hashlib.file_digest(cached,'sha256').hexdigest()==f['lfs']['sha256'],name
        print('verified existing',name,flush=True);return
    print('download',name,f['size'],flush=True)
    partial=path.with_name(path.name+'.partial'); digest=hashlib.sha256()
    with urllib.request.urlopen(f'https://huggingface.co/{MODEL}/resolve/{REV}/{name}',timeout=120) as src, partial.open('wb') as dst:
        while chunk:=src.read(8*1024*1024): dst.write(chunk);digest.update(chunk)
    assert partial.stat().st_size==f['size'], name
    if 'lfs' in f: assert digest.hexdigest()==f['lfs']['sha256'],name
    partial.replace(path)
    print('verified',name,flush=True)

files=[f for f in manifest['siblings'] if f['rfilename'] in ('LICENSE.txt','config.json','Wan2.1_VAE.pth',
       'diffusion_pytorch_model.safetensors','models_t5_umt5-xxl-enc-bf16.pth') or f['rfilename'].startswith('google/')]
with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(fetch,files))
