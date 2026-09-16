# Kernel implementations and software stack must stay fixed for this study.
SHELL := /bin/bash
NATIVE_ENV := LD_LIBRARY_PATH=/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib PYTHONPATH=/workspace/deps OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONHASHSEED=0
GPU_RUN ?= baseline-cudnn-profile
CONFIG ?= /home/ubuntu/drperf/out/wan-timing/cudnn-gate.json
.PHONY: gpu-profile simulate
simulate:
	cd /home/ubuntu/GX/NEX && SSH_BASE_PORT=24420 python3 container_cmds/run.py $(CONFIG)
gpu-profile:
	python3 examples/wan_gx/native_container.py command 'set -e; ulimit -c 0; $(NATIVE_ENV) GX_PROFILE_SO=/workspace/timing/profiler/gx_profile.so GX_PROFILE_DB=/workspace/timing/runs/$(GPU_RUN)-%p.sqlite GX_PROFILE_START_FILE=/workspace/timing/runs/$(GPU_RUN).start GX_PROFILE_STOP_FILE=/workspace/timing/runs/$(GPU_RUN).stop GX_PROFILE_MODE=isolated GX_PROFILE_WARMUP=0 GX_PROFILE_SAMPLES=10 timeout -k 20 1800 bash /workspace/timing/profiler/gx_profile_run.sh python3 /workspace/timing/timing_model.py --role gpu-profile --tree /workspace/baseline --checkpoint /workspace/checkpoint --output /workspace/timing/runs/$(GPU_RUN) > /workspace/timing/runs/$(GPU_RUN).log 2>&1'
