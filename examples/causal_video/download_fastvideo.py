"""Download pinned Self Forcing components, storing text weights in inference bf16.

Conversion is offline and recorded per shard. Native and GX consume identical files.
"""
import argparse
import hashlib
import json
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
import torch
from safetensors.torch import load_file, save_file

p = argparse.ArgumentParser()
p.add_argument('output', type=Path)
a = p.parse_args()
repo = 'wlsaidhi/SFWan2.1-T2V-1.3B-Diffusers'
revision = '4b44356635ae5e927ca552a220f768022be76004'
a.output.mkdir(parents=True, exist_ok=True)
manifest = {'repo': repo, 'revision': revision, 'conversion': 'text_encoder floating tensors to bfloat16', 'files': {}}
manifest_path = a.output/'asset-manifest.json'
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
for name in HfApi().list_repo_files(repo, revision=revision):
    if name.startswith('.') or name.endswith('.md'):
        continue
    if name in manifest['files'] and (a.output/name).exists():
        continue
    path = Path(hf_hub_download(repo, name, revision=revision, local_dir=a.output))
    source_hash = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
    if name.startswith('text_encoder/') and name.endswith('.safetensors'):
        state = load_file(str(path))
        converted = {k: v.to(torch.bfloat16) if v.is_floating_point() else v for k,v in state.items()}
        temporary = path.with_suffix('.converted')
        save_file(converted, str(temporary), metadata={'format': 'pt'})
        temporary.replace(path)
        del state, converted
    manifest['files'][name] = {'source_sha256': source_hash,
                             'stored_sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest(),
                             'bytes': path.stat().st_size}
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print('ASSET', name, path.stat().st_size, flush=True)
