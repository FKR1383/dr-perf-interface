#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
# Dependencies are installed before the explicit sampling/adoption boundary.
dependencies=$1
shift
python3 -m pip install --no-deps -r "$dependencies"
exec bash "$GX_HOME/tools/gx_run.sh" "$@"
