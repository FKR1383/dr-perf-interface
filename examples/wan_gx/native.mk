# Real-GPU follow-up. No GX launcher, DynamoRIO, or timing simulation.
PYTHON ?= python3
NATIVE_ENV = LD_LIBRARY_PATH=/home/jma/bridge-venv2/lib/python3.12/site-packages/nvidia/cudnn/lib PYTHONPATH=/workspace/deps OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONHASHSEED=0
VARIANT ?= baseline
.PHONY: setup resume stop run command
setup resume stop:
	$(PYTHON) examples/wan_gx/native_container.py $@
run:
	$(PYTHON) examples/wan_gx/native_container.py command 'ulimit -c 0; $(NATIVE_ENV) timeout 3600 python3 /workspace/native.py --tree /workspace/$(VARIANT) --checkpoint /workspace/checkpoint --output /workspace/results/$(VARIANT) --warmup > /workspace/results/$(VARIANT).log 2>&1'
command:
	$(PYTHON) examples/wan_gx/native_container.py command '$(CMD)'
