"""Bounded correctness and reachability test for vllm-006."""
from driver import run

TARGET = "vllm-006"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
