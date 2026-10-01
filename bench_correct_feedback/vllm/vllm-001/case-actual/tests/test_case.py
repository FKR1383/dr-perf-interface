"""Bounded correctness and reachability test for vllm-001."""
from driver import run

TARGET = "vllm-001"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
