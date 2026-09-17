"""Bounded correctness and reachability test for vllm-066."""
from driver import run

TARGET = "vllm-066"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
