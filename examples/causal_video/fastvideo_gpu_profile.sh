#!/usr/bin/env bash
# Run inside drperf-wan-native-0 through examples/wan_gx/native_container.py.
set -euo pipefail

run_id=${1:-fastvideo-gpu-02}
profile_mode=${2:-original}
source_tree=${3:-FastVideo}
resident_mode=${4:-off}
worker_cpu_output=${5:-off}
case "${profile_mode}" in
    original) extra=() ;;
    metadata) extra=(--metadata-mode) ;;
    *) echo "Unknown profile mode: ${profile_mode}" >&2; exit 2 ;;
esac
case "${source_tree}" in
    FastVideo|FastVideo-metadata) ;;
    *) echo "Unknown FastVideo source tree: ${source_tree}" >&2; exit 2 ;;
esac
case "${resident_mode}" in
    off) ;;
    on) extra+=(--resident-dit) ;;
    *) echo "Unknown resident mode: ${resident_mode}" >&2; exit 2 ;;
esac
case "${worker_cpu_output}" in
    off) ;;
    on) extra+=(--worker-cpu-output) ;;
    *) echo "Unknown worker CPU output mode: ${worker_cpu_output}" >&2; exit 2 ;;
esac
base=/workspace/causal/runs/${run_id}
for path in "${base}" "${base}.log" "${base}.start" "${base}.stop" "${base}.rank0.pid"*".sqlite"; do
    if [[ -e "${path}" ]]; then
        echo "FastVideo profile output already exists: ${path}" >&2
        exit 2
    fi
done

export PYTHONPATH=/workspace/causal/code:/workspace/causal/${source_tree}:/workspace/causal/deps:/workspace/deps
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONHASHSEED=0
export LD_LIBRARY_PATH=/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib
export FASTVIDEO_ATTENTION_BACKEND=FLASH_ATTN
export TOKENIZERS_PARALLELISM=false
export GX_PROFILE_SO=/workspace/causal/runtime/gx_profile.so
export GX_PROFILE_DB=${base}.sqlite
export GX_PROFILE_START_FILE=${base}.start
export GX_PROFILE_STOP_FILE=${base}.stop
export GX_PROFILE_WARMUP=0
export GX_PROFILE_SAMPLES=3

/workspace/causal/runtime/gx_profile_run.sh \
    python3 /workspace/causal/code/fastvideo_runner.py \
    --role gpu-profile \
    --tree /workspace/causal/${source_tree} \
    --model /workspace/causal/models/SFWan2.1-T2V-1.3B-Diffusers \
    --output "${base}" "${extra[@]}" > "${base}.log" 2>&1
