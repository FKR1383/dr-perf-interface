"""Bounded correctness and reachability test for vllm-043."""
from driver import run

TARGET = "vllm-043"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
