#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
cd /workspace
source /workspace/out/wan-gx/policy.sh
export GX_HOME=/home/jma/GX
export PYTHONPATH=/workspace/perfmark/python
export LD_LIBRARY_PATH=/workspace/build:/workspace/third_party/dynamorio/lib64/release:${LD_LIBRARY_PATH:-}
exec flock -n /workspace/out/wan-gx/results/gx.lock \
  timeout -k 15 "$WAN_TIMEOUT" bash /opt/gx/profile/run.sh emu "$@"
