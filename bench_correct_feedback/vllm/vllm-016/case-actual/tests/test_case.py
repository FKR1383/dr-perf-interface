"""Bounded correctness and reachability test for vllm-016."""
from driver import run

TARGET = "vllm-016"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
