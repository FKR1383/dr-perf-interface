"""Bounded correctness and reachability test for vllm-002."""
from driver import run

TARGET = "vllm-002"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
