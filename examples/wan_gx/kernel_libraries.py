"""Fingerprint the framework libraries that must match kernel collection."""
import hashlib
import json
from pathlib import Path
import sys

site = Path('/home/jma/bridge-venv2/lib/python3.12/site-packages')
patterns = ('torch/lib/libtorch_cuda.so','torch/lib/libtorch_cpu.so',
            'torch/lib/libtorch_python.so','nvidia/cuda_runtime/lib/libcudart.so*',
            'nvidia/cublas/lib/libcublas*.so*','nvidia/cudnn/lib/libcudnn*.so*')
paths = sorted({p for pattern in patterns for p in site.glob(pattern) if p.is_file()})
result = {}
for p in paths:
    with p.open('rb') as stream:
        result[str(p.relative_to(site))] = hashlib.file_digest(stream,'sha256').hexdigest()
for root in (site,Path('/workspace/deps')):
    for p in root.glob('flash_attn_2_cuda*.so'):
        with p.open('rb') as stream:
            result[p.name] = hashlib.file_digest(stream,'sha256').hexdigest()
assert len(result) >= 10 and any(k.startswith('flash_attn_2_cuda') for k in result)
text = json.dumps(result,indent=2)+'\n'
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(text)
print(text)
