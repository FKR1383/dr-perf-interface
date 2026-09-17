"""Uninstrumented official Wan generation on real CUDA, with saved outputs."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--tree', required=True)
p.add_argument('--checkpoint', required=True)
p.add_argument('--output', required=True, help='Output directory, unique per variant')
p.add_argument('--frames', type=int, default=81)
p.add_argument('--steps', type=int, default=50)
p.add_argument('--warmup', action='store_true', help='Untimed 9-frame, 4-step generation')
a = p.parse_args()
assert not os.environ.get('LD_PRELOAD')
assert not os.environ.get('GX_COMM_ONLY')
assert not any(k.startswith('GXVM_') for k in os.environ)
assert not any(os.environ.get(k) for k in ('GX_PREDICT_DB', 'NEX_PREDICT_DB', 'GX_PROFILE_DB', 'NEX_PROFILE_DB'))
sys.path.insert(0, a.tree)
import torch
import wan
from wan.configs import WAN_CONFIGS

assert Path(wan.__file__).resolve().is_relative_to(Path(a.tree).resolve())
assert torch.cuda.device_count() == 1, 'Expose only the selected idle GPU'
assert 'A100' in torch.cuda.get_device_name(0)
assert torch.backends.cudnn.enabled
torch.set_num_threads(1)
probe = torch.ones((16, 16), device='cuda') @ torch.ones((16, 16), device='cuda')
assert probe.sum().item() == 4096, 'Real CUDA arithmetic required'
del probe
maps = Path('/proc/self/maps').read_text().lower()
assert 'gx_cuda' not in maps and 'dynamorio' not in maps and 'libdrperf' not in maps
output = Path(a.output)
output.mkdir(parents=True, exist_ok=False)
prompt = 'A cat walks on the grass, realistic style'
config = dict(size=(832, 480), sample_solver='unipc', shift=5.0,
              guide_scale=5.0, seed=42, offload_model=False)
report = dict(tree=a.tree, frames=a.frames, steps=a.steps, prompt=prompt,
              config=config, torch=torch.__version__, cuda=torch.version.cuda,
              cudnn=torch.backends.cudnn.version(), cudnn_enabled=True,
              cudnn_benchmark=torch.backends.cudnn.benchmark,
              gpu=torch.cuda.get_device_name(0),
              library_path=os.environ.get('LD_LIBRARY_PATH'),
              gpu_state=subprocess.check_output(['nvidia-smi', '--query-gpu=name,uuid,driver_version,memory.total', '--format=csv'], text=True),
              packages={k:importlib.metadata.version(k) for k in
                        ('torch','diffusers','transformers','flash-attn','safetensors')},
              source_sha256={str(f.relative_to(a.tree)):hashlib.sha256(f.read_bytes()).hexdigest()
                             for f in sorted(Path(a.tree).rglob('*.py'))},
              warmup=dict(frames=9, steps=4) if a.warmup else None,
              real_cuda=True, drperf=False, gx=False, timing_simulation=False)
def save_report():
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
save_report()
start = time.perf_counter()
pipe = wan.WanT2V(config=WAN_CONFIGS['t2v-1.3B'], checkpoint_dir=a.checkpoint)
torch.cuda.synchronize()
report['load_seconds'] = time.perf_counter()-start
print('MODEL_LOADED', report['load_seconds'], flush=True)
if a.warmup:
    start = time.perf_counter()
    warmup = pipe.generate(prompt, frame_num=9, sampling_steps=4, **config)
    torch.cuda.synchronize()
    report['warmup_seconds'] = time.perf_counter()-start
    assert torch.isfinite(warmup).all().item()
    del warmup
    print('WARMUP_DONE', report['warmup_seconds'], flush=True)
latents = []
decode = pipe.vae.decode
def capture_decode(zs):
    latents.extend(z.detach() for z in zs)
    return decode(zs)
pipe.vae.decode = capture_decode
torch.cuda.synchronize()
torch.cuda.reset_peak_memory_stats()
save_report()
start = time.perf_counter()
video = pipe.generate(prompt, frame_num=a.frames, sampling_steps=a.steps, **config)
torch.cuda.synchronize()
report['generation_seconds'] = time.perf_counter()-start
report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
report['shape'] = list(video.shape)
assert tuple(video.shape) == (3, a.frames, 480, 832)
report['finite'] = bool(torch.isfinite(video).all().item())
assert report['finite']
torch.save([z.cpu() for z in latents], output/'latents.pt')
torch.save(video.cpu(), output/'video.pt')
report['artifacts'] = {name:hashlib.sha256((output/name).read_bytes()).hexdigest()
                       for name in ('latents.pt', 'video.pt')}
save_report()
print('RESULT', json.dumps(report), flush=True)
