#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
# Small Python compatibility additions only; Torch/CUDA remain image-provided.
python3 -m pip install --no-deps ftfy==6.3.1 easydict==1.13 dashscope==1.25.0 imageio-ffmpeg==0.6.0 wcwidth==0.8.2 websocket-client==1.8.0
run_dir=$1
shift
cd "$run_dir"
exec bash /home/jma/GX/tools/gx_run.sh "$@"
