"""Generate a managed GX experiment using existing model assets on this host."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('role', choices=('emu','cpu-profile','replay','drperf'))
p.add_argument('--name', required=True)
p.add_argument('--tree', default='baseline')
p.add_argument('--frames', type=int, default=81)
p.add_argument('--steps', type=int, default=50)
p.add_argument('--warmup-steps', type=int, default=4)
p.add_argument('--gpu-db', type=Path)
p.add_argument('--cpu-db', type=Path)
p.add_argument('--gx-library', type=Path)
p.add_argument('--drperf-bundle', type=Path)
p.add_argument('--real-cudnn', action='store_true')
p.add_argument('--context-limits', type=Path)
p.add_argument('--device-attributes', type=Path)
p.add_argument('--conv-backend', choices=('cudnn','native'), default='cudnn')
p.add_argument('--epoch-ns', type=int, default=10000)
p.add_argument('--timeout', type=int, default=3600)
p.add_argument('--host', default='ubuntu@icdslab2.epfl.ch')
p.add_argument('--workspace', default='/home/ubuntu/drperf-wan-timing')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
code = Path(__file__).resolve().parent
env = dict(GX_HOME='/home/jma/GX',GX_COMM_ONLY='1',GX_DEVICE_MODEL='A100',
           GX_NUM_LOCAL_GPUS='1',GX_SHM_ARENA_GB='8',GX_APP_REAL_MAX_BYTES='16777216',
           GX_CHROME_TRACE='1',GX_ID='0',GX_PROFILE_DB='',NEX_PROFILE_DB='',
           GX_PREDICT_DB='',NEX_PREDICT_DB='',NCCL_SOCKET_IFNAME='lo',
           OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONHASHSEED='0',
           CUDA_VISIBLE_DEVICES='0',
           LD_LIBRARY_PATH='/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib')
files = dict(runner=str(code/'timing_model.py'),entry=str(code/'timing_entry.sh'),
             requirements=str(code/'dependencies.txt'))
if a.real_cudnn:
    assert a.gx_library, '--real-cudnn requires the explicitly patched GX runtime'
    assert a.context_limits, '--real-cudnn requires measured primary-context limits'
    assert a.device_attributes, '--real-cudnn requires measured driver device attributes'
    assert a.gpu_db, '--real-cudnn requires the GPU DB for recorded occupancy/function queries, even in plain mode'
    env['GX_REAL_CUDNN'] = '1'
    files['context_limits'] = str(a.context_limits.resolve())
    env['GX_CUDA_CONTEXT_LIMITS'] = '{file:context_limits}'
    files['device_attributes'] = str(a.device_attributes.resolve())
    env['GX_CUDA_DEVICE_ATTRIBUTES'] = '{file:device_attributes}'
mode = {'emu':'plain','cpu-profile':'profile','replay':'replay','drperf':'plain'}[a.role]
gxvm = dict(mode=mode,attachment='late',epoch=dict(ns=a.epoch_ns))
if a.gpu_db:
    files['gpu_db'] = str(a.gpu_db.resolve())
    env['GX_PREDICT_DB'] = '{file:gpu_db}'
if a.role == 'cpu-profile':
    gxvm['profile'] = dict(output='{run_dir}/profile-%p.db',autostart=False,
                          instruction_period=5000000,task_period_ns=5000000)
if a.role == 'replay':
    assert a.cpu_db and a.gpu_db
    files['cpu_db'] = str(a.cpu_db.resolve())
    gxvm['replay'] = dict(database='{file:cpu_db}',accounting='refund',ns_per_instruction_scale=1.0)
    # No NCCL in this workload; HBM mode also enables measured compute waits.
    gxvm['gpu_memory'] = dict(mode='hbm',hbm_bytes_per_second=1555000000000,
                             nvlink_bytes_per_second=300000000000)
config = dict(name=a.name,hosts=[dict(address=a.host,containers=1)],
              image='gx-mixed-profile:rcp-20260915-110d87373a4a',workspace=a.workspace,
              resources=dict(cpus=8,memory='64g'),network=dict(name='wan-timing-net',manager=0),
              files=files,gxvm=gxvm,timeout_seconds=a.timeout,
              application=dict(cwd='/workspace',environment=env,command=[
                  'bash','{file:entry}','{file:requirements}','python3','{file:runner}',
                  '--role',a.role,'--tree',f'/workspace/wan-gx/{a.tree}',
                  '--checkpoint','/workspace/wan-gx/checkpoint','--output','{run_dir}/wan',
                  '--frames',str(a.frames),'--steps',str(a.steps),
                  '--warmup-steps',str(a.warmup_steps),'--conv-backend',a.conv_backend]))
if a.gx_library:
    config['runtime'] = dict(gx_library=str(a.gx_library.resolve()))
if a.role == 'drperf':
    assert a.drperf_bundle and not a.cpu_db
    files['drperf'] = str(a.drperf_bundle.resolve())
    env.update(DRPERF_EXCLUDE_CUDA_MODULE='gx_cuda.so', DRPERF_FOLLOW_THREADS='0',
               PYTHONPATH='{file:drperf}/examples/wan_gx')
    env['LD_LIBRARY_PATH'] = ('{file:drperf}/build:'
                             '{file:drperf}/third_party/dynamorio/lib64/release:'
                             '{file:drperf}/third_party/dynamorio/ext/lib64/release:'
                             + env['LD_LIBRARY_PATH'])
    command = config['application']['command']
    command[3:3] = ['python3', '{file:drperf}/examples/wan_gx/measure.py',
                    '{run_dir}/drperf']
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(config,indent=2)+'\n')
print(a.output)
