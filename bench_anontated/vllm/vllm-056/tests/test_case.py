"""Bounded correctness and reachability test for vllm-056."""
from driver import run

TARGET = "vllm-056"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
