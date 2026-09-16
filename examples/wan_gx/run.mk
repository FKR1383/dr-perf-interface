ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
export WAN_GX_ROOT := /home/ubuntu/GX/NEX
export WAN_OUTPUT := $(ROOT)/out/wan-gx
export WAN_IMAGE := gx-mixed-profile:rcp-20260915-110d87373a4a
export WAN_CPUS := 8
export WAN_MEMORY := 64g
export WAN_TIMEOUT := 600
export GX_DEVICE_MODEL := H100
export GX_NUM_LOCAL_GPUS := 1
export GX_SHM_ARENA_GB := 8
export GX_APP_REAL_MAX_BYTES := 16777216
export NCCL_SOCKET_IFNAME := lo
export OMP_NUM_THREADS := 1
export MKL_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1
export WAN_MODEL := Wan-AI/Wan2.1-T2V-1.3B
export WAN_SIZE := 832*480
export WAN_FRAMES := 81
export WAN_STEPS := 50
export WAN_SEED := 42
export WAN_OFFLOAD := False
export WAN_PROMPT := A cat walks on the grass, realistic style
.PHONY: setup resume stop command
setup resume stop:
	python3 $(ROOT)/examples/wan_gx/container.py $@
command:
	python3 $(ROOT)/examples/wan_gx/container.py command '$(CMD)'
