"""Hash Inferix model assets once per host, outside every measured workload."""
import argparse
import hashlib
import json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--base',type=Path,required=True)
p.add_argument('--checkpoint',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
files={str(f.relative_to(a.base)):f for f in sorted(a.base.rglob('*')) if f.is_file() and not any(x.startswith('.') for x in f.relative_to(a.base).parts)}
files['self_forcing_dmd.pt']=a.checkpoint
identity={}
for name,path in files.items():
    with path.open('rb') as source: digest=hashlib.file_digest(source,'sha256').hexdigest()
    identity[name]=dict(bytes=path.stat().st_size,sha256=digest)
a.output.write_text(json.dumps(identity,indent=2)+'\n')
print(a.output,flush=True)
