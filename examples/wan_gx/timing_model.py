"""Shared Wan workload and phase boundary for GPU profiling and GXVM replay.

Only the gpu-profile role executes GPU arithmetic and checks finite outputs.
Emulation checks execution structure; it does not establish numerical correctness.
"""
import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--role', choices=('gpu-profile','emu','cpu-profile','replay','drperf'), required=True)
p.add_argument('--tree', required=True)
p.add_argument('--checkpoint', required=True)
p.add_argument('--output', required=True)
p.add_argument('--frames', type=int, default=81)
p.add_argument('--steps', type=int, default=50)
p.add_argument('--warmup-steps', type=int, default=4)
p.add_argument('--conv-backend', choices=('cudnn','native'), default='cudnn')
a = p.parse_args()
out = Path(a.output)
out.mkdir(parents=True, exist_ok=False)
os.chdir(out.parent)
sys.path.insert(0, a.tree)
import torch
import wan
from wan.configs import WAN_CONFIGS

assert Path(wan.__file__).resolve().is_relative_to(Path(a.tree).resolve())
torch.set_num_threads(1)
torch.backends.cudnn.enabled = a.conv_backend == 'cudnn'
physical = a.role == 'gpu-profile'
assert bool(os.environ.get('GX_COMM_ONLY') == '1') != physical
assert 'A100' in torch.cuda.get_device_name(0)
maps = Path('/proc/self/maps').read_text()
if physical:
    assert 'gx_cuda.so' not in maps and 'libdynamorio' not in maps
    assert os.environ.get('GX_PROFILE_DB')
    assert (torch.ones(16,16,device='cuda') @ torch.ones(16,16,device='cuda')).sum().item() == 4096
    assert os.environ.get('GX_PROFILE_START_FILE')
    assert not Path(os.environ['GX_PROFILE_START_FILE']).exists()
    assert os.environ.get('GX_PROFILE_STOP_FILE')
    assert not Path(os.environ['GX_PROFILE_STOP_FILE']).exists()
else:
    assert 'gx_cuda.so' in maps
    assert not os.environ.get('GX_PROFILE_DB')
    if a.role in ('emu','drperf'):
        assert not os.environ.get('GXVM_LATE_ATTACH_ACTIVE')

config = dict(size=(832,480),frame_num=a.frames,sampling_steps=a.steps,
              sample_solver='unipc',shift=5.0,guide_scale=5.0,seed=42,offload_model=False)
prompt = 'A cat walks on the grass, realistic style'
report = dict(role=a.role, pid=os.getpid(), config=config, prompt=prompt, warmup_steps=a.warmup_steps,
              convolution_backend=a.conv_backend, gpu=torch.cuda.get_device_name(0),
              cudnn_version=torch.backends.cudnn.version(),
              cudnn_policy=dict(allow_tf32=torch.backends.cudnn.allow_tf32,
                                benchmark=torch.backends.cudnn.benchmark,
                                deterministic=torch.backends.cudnn.deterministic),
              packages={k:importlib.metadata.version(k) for k in
                        ('torch','diffusers','transformers','flash-attn','safetensors')},
              source_sha256={str(f.relative_to(a.tree)):hashlib.sha256(f.read_bytes()).hexdigest()
                             for f in sorted(Path(a.tree).rglob('*.py'))},
              environment={k:os.environ[k] for k in sorted(os.environ)
                           if k.startswith(('GXVM_','GX_PREDICT_','GX_PROFILE_','GX_DEVICE_','GX_CHROME_', 'GX_REAL_', 'GX_CUDA_'))},
              phase_events=[])
def save():
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
save()
started = time.perf_counter()
pipe = wan.WanT2V(config=WAN_CONFIGS['t2v-1.3B'], checkpoint_dir=a.checkpoint)
torch.cuda.synchronize()
report['load_host_seconds'] = time.perf_counter()-started
print('WAN_LOADED', report['load_host_seconds'], flush=True)
if a.warmup_steps:
    warmup = pipe.generate(prompt, **(config | {'sampling_steps':a.warmup_steps}))
    torch.cuda.synchronize()
    if physical:
        assert torch.isfinite(warmup).all().item()
    del warmup
print('WAN_WARMUP_DONE', flush=True)

runtime = ctypes.CDLL(None)
if a.role == 'drperf':
    from instrument import install
    report['regions'] = install(pipe)
elif a.role == 'cpu-profile':
    runtime.gxvm_ipc_profile_start()
elif a.role == 'replay':
    runtime.gxvm_adopt_now()
elif physical:
    Path(os.environ['GX_PROFILE_START_FILE']).touch(exist_ok=False)

clock = time.perf_counter_ns
if a.role == 'replay':
    runtime.gxvm_time_ns.argtypes = []
    runtime.gxvm_time_ns.restype = ctypes.c_uint64
    clock = runtime.gxvm_time_ns

# Coarse CPU-phase markers use the same clock as the reported interval.
# They are ranges, not GPU-exclusive timings; queued work can overlap them.
def trace_call(obj, name, label):
    original = getattr(obj,name)
    def wrapped(*args, **kwargs):
        start = int(clock())
        result = original(*args,**kwargs)
        report['phase_events'].append(dict(name=label,start_ns=start,end_ns=int(clock())))
        return result
    setattr(obj,name,wrapped)
trace_call(pipe.model, 'forward', 'transformer')
trace_call(pipe.vae, 'decode', 'vae_decode')
trace_call(pipe.text_encoder.model, 'forward', 'text_encoder')
save()
start = int(clock())
report['start_perf_counter_ns'] = time.perf_counter_ns()
video = pipe.generate(prompt, **config)
torch.cuda.synchronize()
end = int(clock())
if physical:
    Path(os.environ['GX_PROFILE_STOP_FILE']).touch(exist_ok=False)
elif a.role == 'cpu-profile':
    runtime.gxvm_ipc_profile_stop.argtypes = []
    runtime.gxvm_ipc_profile_stop.restype = ctypes.c_int
    assert runtime.gxvm_ipc_profile_stop() == 0
    report['cpu_profile_stopped'] = True
report['end_perf_counter_ns'] = time.perf_counter_ns()
report['start_ns'], report['end_ns'] = start,end
report['elapsed_seconds'] = (end-start)/1e9
report['clock'] = 'gxvm_time_ns' if a.role == 'replay' else 'host_perf_counter_ns'
report['shape'] = list(video.shape)
assert tuple(video.shape) == (3,a.frames,480,832)
report['numerical_equivalence_checked'] = False
report['finite_check_performed'] = physical
if physical:
    report['finite'] = bool(torch.isfinite(video).all().item())
    assert report['finite']
save()
print('WAN_TIMING_RESULT', json.dumps({k:v for k,v in report.items()
                                    if k not in ('source_sha256','environment','phase_events')}), flush=True)
