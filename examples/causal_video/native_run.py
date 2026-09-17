"""Launch an isolated Inferix native run through the existing managed A100 helper."""
import argparse
from pathlib import Path
import re
import shlex
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--name', required=True)
p.add_argument('--tree', default='Inferix-metadata')
p.add_argument('--role', choices=['native','gpu-profile'], default='native')
p.add_argument('--frames', type=int, default=21)
p.add_argument('--warmup-frames', type=int, default=21)
p.add_argument('--segments', type=int, default=1)
p.add_argument('--save-output', action='store_true')
p.add_argument('--repetitions', type=int, default=1)
p.add_argument('--kv-residency', choices=['offload','gpu'], default='offload')
p.add_argument('--validate', action='store_true')
p.add_argument('--rope-cache', action='store_true',
               help='select the isolated Inferix RoPE-cache tree and wrapper')
a=p.parse_args()
if a.rope_cache:
    if a.tree == 'Inferix-metadata':
        a.tree = 'Inferix-cpuopt'
    elif a.tree != 'Inferix-cpuopt':
        p.error('--rope-cache requires --tree Inferix-cpuopt')
assert re.fullmatch('[a-zA-Z0-9_-]+', a.name)
assert re.fullmatch('[a-zA-Z0-9_-]+', a.tree)
root=Path(__file__).resolve().parents[2]
base='/workspace/causal'
out=f'{base}/runs/{a.name}'
env=dict(PYTHONPATH=f'{base}/code:{base}/deps:/workspace/deps:{base}/{a.tree}',
         LD_LIBRARY_PATH='/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib',
         OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
         PYTHONUNBUFFERED='1', PYTHONHASHSEED='0')
if a.rope_cache:
    env['INFERIX_ROPE_FREQ_CACHE'] = '1'
entry = 'cpu_rope_entry.py' if a.rope_cache else 'inferix_runner.py'
command=['python3', f'{base}/code/{entry}', '--role',a.role,'--tree',f'{base}/{a.tree}',
         '--base','/workspace/checkpoint','--checkpoint',f'{base}/models/self-forcing/checkpoints/self_forcing_dmd.pt',
         '--output',out,'--latent-frames',str(a.frames),'--warmup-frames',str(a.warmup_frames),
         '--segments',str(a.segments),'--repetitions',str(a.repetitions),'--kv-residency',a.kv_residency]
if a.save_output: command.append('--save-output')
if a.validate:
    assert a.role=='native'
    command=['python3',f'{base}/code/validate_inferix.py',*command[2:]]
if a.role=='gpu-profile':
    env.update(GX_PROFILE_SO=f'{base}/runtime/gx_profile.so', GX_PROFILE_DB=out+'.pid%p.sqlite',
               GX_PROFILE_START_FILE=out+'.start', GX_PROFILE_STOP_FILE=out+'.stop',
               GX_PROFILE_MODE='isolated', GX_PROFILE_WARMUP='0', GX_PROFILE_SAMPLES='3')
    command=['bash',f'{base}/runtime/gx_profile_run.sh',*command]
script='ulimit -c 0; '+shlex.join(['env',*[f'{k}={v}' for k,v in env.items()],
                                'timeout','-k','20','1800',*command])+f' > {shlex.quote(out+".log")} 2>&1'
subprocess.run(['python3', str(root/'examples/wan_gx/native_container.py'),'command',script],check=True)
