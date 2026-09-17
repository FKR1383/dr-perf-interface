"""Emit managed, bounded causal-video GX runs; model assets are staged separately."""
import argparse
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('framework', choices=['inferix','fastvideo'])
p.add_argument('role', choices=['emu','cpu-profile','partial_sync','drperf'])
p.add_argument('--name', required=True)
p.add_argument('--gpu-db', type=Path, required=True)
p.add_argument('--cpu-db', type=Path)
p.add_argument('--timeline-client', type=Path, help='isolated GXVM client override for partial timing')
p.add_argument('--tree')
p.add_argument('--rope-cache', action='store_true', help='Inferix opt-in RoPE frequency-cache variant')
p.add_argument('--resident-dit', action='store_true', help='FastVideo opt-in persistent GPU DiT weights')
p.add_argument('--worker-cpu-output', action='store_true', help='FastVideo matched worker-side GPU quantization and CPU output transport')
p.add_argument('--frames', type=int, help='Inferix latent frames (default21); FastVideo pixel frames (default81)')
p.add_argument('--warmup-frames', type=int, help='Inferix full same-size warmup by default')
p.add_argument('--segments', type=int, default=1)
p.add_argument('--sample-ns', type=int, default=0)
p.add_argument('--memory', default='58g')
p.add_argument('--kv-residency', choices=['offload','gpu'], default='offload')
p.add_argument('--output', type=Path, required=True)
p.add_argument('--drperf-bundle', type=Path)
a=p.parse_args()
if not re.fullmatch(r'[a-z][a-z0-9-]{0,23}', a.name):
    p.error('--name must be 1–24 lowercase letters, digits or hyphens, starting with a letter')
if a.timeline_client and a.role != 'partial_sync':
    p.error('--timeline-client is only used for partial_sync')
if a.resident_dit and a.framework != 'fastvideo':
    p.error('--resident-dit is only supported for FastVideo')
if a.worker_cpu_output and a.framework != 'fastvideo':
    p.error('--worker-cpu-output is only supported for FastVideo')
if a.rope_cache and a.framework != 'inferix':
    p.error('--rope-cache is only supported for Inferix')
if a.frames is None: a.frames=21 if a.framework=='inferix' else 81
if a.warmup_frames is None: a.warmup_frames=a.frames
if a.frames <= 0 or a.warmup_frames < 0 or a.segments <= 0:
    p.error('frame and segment counts must be positive; warmup may be zero')
root=Path(__file__).resolve().parents[2]
gx=root/'out/causal-video/gx-runtime/bazel-bin/src/sims/gpu/gx_cuda.so'
files={'gpu_db':str(a.gpu_db.resolve()),
       'context_limits':str(root/'examples/wan_gx/evidence/timing-inputs/context-limits.tsv'),
       'device_attributes':str(root/'examples/wan_gx/evidence/timing-inputs/device-attributes.tsv')}
tree=a.tree or ('Inferix-cpuopt' if a.rope_cache else 'Inferix-metadata' if a.framework=='inferix' else 'FastVideo-metadata')
env=dict(GX_HOME='/home/jma/GX', GX_COMM_ONLY='1', GX_DEVICE_MODEL='A100',
         GX_NUM_LOCAL_GPUS='1', GX_SHM_ARENA_GB='8', GX_APP_REAL_MAX_BYTES='16777216',
         GX_CHROME_TRACE='1', GX_ID='0', GX_REAL_CUDNN='1',
         GX_PREDICT_DB='{file:gpu_db}', GX_CUDA_CONTEXT_LIMITS='{file:context_limits}',
         GX_CUDA_DEVICE_ATTRIBUTES='{file:device_attributes}',
         NCCL_SOCKET_IFNAME='lo', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
         OPENBLAS_NUM_THREADS='1', PYTHONHASHSEED='0', CUDA_VISIBLE_DEVICES='0',
         PYTHONPATH=f'/workspace/causal/code:/workspace/causal/{tree}:/workspace/causal/deps:/workspace/causal/base/deps',
         LD_LIBRARY_PATH='/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib',
         FASTVIDEO_ATTENTION_BACKEND='FLASH_ATTN', TOKENIZERS_PARALLELISM='false',
         HF_HUB_OFFLINE='1', PYTHONUNBUFFERED='1')
if a.rope_cache:
    env['INFERIX_ROPE_FREQ_CACHE']='1'
mode={'emu':'plain','cpu-profile':'profile','partial_sync':'partial_sync','drperf':'plain'}[a.role]
gxvm=dict(mode=mode, attachment='late')
if a.role=='cpu-profile':
    gxvm['profile']=dict(output='{run_dir}/profile-%p.db',autostart=False,
                        instruction_period=5000000,task_period_ns=5000000)
if a.role=='partial_sync':
    assert a.cpu_db
    files['cpu_db']=str(a.cpu_db.resolve())
    gxvm.update(replay=dict(database='{file:cpu_db}',accounting='refund',ns_per_instruction_scale=1.0),
                timeline=dict(sample_ns=a.sample_ns),
                gpu_memory=dict(mode='hbm',hbm_bytes_per_second=1555000000000,nvlink_bytes_per_second=300000000000))
entry='cpu_rope_entry.py' if a.rope_cache else f'{a.framework}_runner.py'
command=['python3',f'/workspace/causal/code/{entry}',
         '--role',a.role,'--tree',f'/workspace/causal/{tree}','--output','{run_dir}/model']
if a.framework=='inferix':
    command += ['--base','/workspace/wan-gx/checkpoint','--checkpoint',
                '/workspace/causal/models/self-forcing/checkpoints/self_forcing_dmd.pt',
                '--latent-frames',str(a.frames),'--warmup-frames',str(a.warmup_frames),'--segments',str(a.segments),'--kv-residency',a.kv_residency]
else:
    command += ['--model','/workspace/causal/models/SFWan2.1-T2V-1.3B-Diffusers','--frames',str(a.frames),'--metadata-mode']
    if a.resident_dit: command.append('--resident-dit')
    if a.worker_cpu_output: command.append('--worker-cpu-output')
config=dict(name=a.name,hosts=[dict(address='ubuntu@icdslab2.epfl.ch',containers=1)],
            image='gx-mixed-profile:rcp-20260915-110d87373a4a',workspace='/home/ubuntu/drperf-wan-timing',
            resources=dict(cpus=8,memory=a.memory),network=dict(name='wan-timing-net',manager=0),
            files=files,gxvm=gxvm,runtime=dict(gx_library=str(gx.resolve())),timeout_seconds=1800,
            application=dict(cwd='/workspace',environment=env,command=['bash','/workspace/causal/code/entry.sh','{run_dir}']+command))
if a.timeline_client:
    config['runtime']['timeline_client']=str(a.timeline_client.resolve())
if a.role=='drperf':
    assert a.drperf_bundle and not a.cpu_db
    files['drperf']=str(a.drperf_bundle.resolve())
    env.update(DRPERF_EXCLUDE_CUDA_MODULE='gx_cuda.so', DRPERF_FOLLOW_THREADS='0')
    env['LD_LIBRARY_PATH']='{file:drperf}/build:{file:drperf}/third_party/dynamorio/lib64/release:{file:drperf}/third_party/dynamorio/ext/lib64/release:'+env['LD_LIBRARY_PATH']
    # The outer GX wrapper establishes emulation; drperf measures its application.
    command[0:0]=['python3','{file:drperf}/examples/wan_gx/measure.py','{run_dir}/drperf']
    config['application']['command']=['bash','/workspace/causal/code/entry.sh','{run_dir}']+command
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(config,indent=2)+'\n')
print(a.output)
