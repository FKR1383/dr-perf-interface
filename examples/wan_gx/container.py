"""Experiment-local GX container management through the prescribed helpers."""
import os
import json
import shlex
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GX = Path(os.environ['WAN_GX_ROOT'])
OUT = Path(os.environ['WAN_OUTPUT'])
PREFIX = 'drperf-wan-gx-'

def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, timeout=kw.pop('timeout', 900), **kw)

def arguments():
    return ['--emu-hosts', OUT/'hosts', '--container-prefix', PREFIX,
            '--network-driver', 'bridge', '--workspace', ROOT,
            '--ssh-base-port', '24370', '--ssh-config-out', OUT/'ssh-config',
            '--mpi-hostfile-out', OUT/'mpi-hosts', '--leader-ips-out', OUT/'leaders',
            '--container-ip-map-out', OUT/'ips']

def setup():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'hosts').write_text('ubuntu@icdslab4.epfl.ch slots=1\n')
    key = OUT/'cluster-key'
    if not key.exists(): run(['ssh-keygen','-q','-t','ed25519','-N','','-f',key])
    probe = subprocess.run(['docker','container','inspect',PREFIX+'0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode == 0: raise SystemExit('Container already exists; use resume.')
    image, tag = os.environ['WAN_IMAGE'].rsplit(':',1)
    env = os.environ | {'USE_HOST_NETWORK':'1','AUTH_KEY_PRIVATE_FILE':str(key),'AUTH_KEY_FILE':str(key)+'.pub',
                        'AUTH_KEY_MOUNT_PRIVATE_FILE':str(key),'AUTH_KEY_MOUNT_FILE':str(key)+'.pub',
                        'PREPARE_SETUP_MOUNT_FILE':str(GX/'container/prepare-setup.sh')}
    run(['python3',GX/'scripts/launch_containers.py',*arguments(),'--image',image,'--image-tag',tag,
         '--cpus',os.environ['WAN_CPUS'],'--memory',os.environ['WAN_MEMORY'],'--memory-sharing','off'],env=env)

def command(cmd):
    policy_keys = ('WAN_IMAGE', 'WAN_CPUS', 'WAN_MEMORY', 'WAN_TIMEOUT',
                   'GX_DEVICE_MODEL', 'GX_NUM_LOCAL_GPUS', 'GX_SHM_ARENA_GB',
                   'GX_APP_REAL_MAX_BYTES', 'NCCL_SOCKET_IFNAME', 'OMP_NUM_THREADS',
                   'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'WAN_MODEL', 'WAN_SIZE',
                   'WAN_FRAMES', 'WAN_STEPS', 'WAN_SEED', 'WAN_OFFLOAD', 'WAN_PROMPT')
    policy = {k: os.environ[k] for k in policy_keys}
    (OUT/'policy.json').write_text(json.dumps(policy,indent=2)+'\n')
    (OUT/'policy.sh').write_text(''.join(f'export {k}={shlex.quote(v)}\n' for k,v in policy.items()))
    env = os.environ | {'EMU_HOSTS':str(OUT/'hosts'),'CONTAINER_PREFIX':PREFIX}
    run(['bash','-c','source "$1/container/cmd_def.sh"; shift; "$@"','wan-gx',GX,
         'RUNDSINGLECMD',PREFIX+'0',cmd,*arguments(),'--exec-log-dir',OUT/'commands'],env=env)

if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'setup': setup()
    elif action == 'command': command(sys.argv[2])
    else: run(['python3',GX/'scripts/launch_containers.py',*arguments(),'--'+action+'-only'])
