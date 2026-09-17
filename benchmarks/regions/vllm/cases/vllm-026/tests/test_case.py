"""Bounded correctness and reachability test for vllm-026."""
from driver import run

TARGET = "vllm-026"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
