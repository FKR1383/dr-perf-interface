#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "usage: $0 AGENT_RESPONSE.json" >&2
  exit 2
fi
exec python3 /home/pouria/dr-perf-jiacheng/dr-perf-interface/bench_correct_feedback/evaluate_pcvs.py --suite vllm --run-dir /home/pouria/dr-perf-jiacheng/dr-perf-interface/bench_correct_feedback/vllm/.controller-runs/vllm-029 --candidate "$1"
