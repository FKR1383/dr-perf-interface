#!/usr/bin/env bash
set -euo pipefail
cd /workspace/out/wan-gx/upstream
exec bash /workspace/examples/wan_gx/entry.sh python3 /workspace/out/wan-gx/upstream/generate.py \
  --task t2v-1.3B --ckpt_dir /workspace/out/wan-gx/checkpoint \
  --size '832*480' --frame_num 81 --sample_steps 50 --sample_solver unipc \
  --base_seed 42 --offload_model False \
  --prompt 'A cat walks on the grass, realistic style' \
  --save_file /workspace/out/wan-gx/results/baseline-emulated.mp4
