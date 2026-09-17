"""Bounded correctness and reachability test for vllm-029."""
from driver import run

TARGET = "vllm-029"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
