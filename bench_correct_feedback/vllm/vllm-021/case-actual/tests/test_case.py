"""Bounded correctness and reachability test for vllm-021."""
from driver import run

TARGET = "vllm-021"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
