"""Manage an isolated real-GPU validation container through the GX helpers."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'out/wan-a100'
GX = Path(os.environ.get('WAN_GX_ROOT', '/home/ubuntu/GX/NEX'))
HOST = os.environ.get('WAN_NATIVE_HOST', 'jcm@A100')
REMOTE = os.environ.get('WAN_NATIVE_WORKSPACE', '/home/jcm/drperf-wan-a100-20260916')
PREFIX = 'drperf-wan-native-'

def run(args, **kw):
    subprocess.run([str(x) for x in args], check=True, **kw)

def arguments():
    return ['--emu-hosts', OUT/'hosts', '--container-prefix', PREFIX,
            '--network-driver', 'bridge', '--workspace', REMOTE,
            '--ssh-base-port', '24371', '--ssh-config-out', OUT/'ssh-config',
            '--mpi-hostfile-out', OUT/'mpi-hosts', '--leader-ips-out', OUT/'leaders',
            '--container-ip-map-out', OUT/'ips']

def setup():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'hosts').write_text(f'{HOST} slots=1 gpus=1\n')
    probe = subprocess.run(['ssh', HOST, 'docker', 'container', 'inspect', PREFIX+'0'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode == 0:
        raise SystemExit('Container already exists; use resume.')
    key = OUT/'cluster-key'
    if not key.exists():
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', key])
    run(['rsync', '-a', key, str(key)+'.pub', GX/'container/prepare-setup.sh', f'{HOST}:{REMOTE}/setup/'])
    env = os.environ | {'USE_HOST_NETWORK':'1', 'AUTH_KEY_PRIVATE_FILE':str(key),
                       'AUTH_KEY_FILE':str(key)+'.pub',
                       'AUTH_KEY_MOUNT_PRIVATE_FILE':REMOTE+'/setup/cluster-key',
                       'AUTH_KEY_MOUNT_FILE':REMOTE+'/setup/cluster-key.pub',
                       'PREPARE_SETUP_MOUNT_FILE':REMOTE+'/setup/prepare-setup.sh'}
    run(['python3', GX/'scripts/launch_containers.py', *arguments(),
         '--image', 'gx-kimi-k3', '--image-tag', 'latest',
         '--cpus', '8', '--memory', '64g', '--memory-sharing', 'off',
         '--authorized-keys-file', str(key)+'.pub', '--ssh-private-key-file', key], env=env)

if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'setup':
        setup()
    elif action == 'command':
        env = os.environ | {'EMU_HOSTS':str(OUT/'hosts'), 'CONTAINER_PREFIX':PREFIX}
        run(['bash', '-c', 'source "$1/container/cmd_def.sh"; shift; "$@"',
             'wan-native', GX, 'RUNDSINGLECMD', PREFIX+'0', sys.argv[2],
             *arguments(), '--exec-log-dir', OUT/'commands'], env=env)
    else:
        assert action in ('stop', 'resume')
        run(['python3', GX/'scripts/launch_containers.py', *arguments(), '--'+action+'-only'])
