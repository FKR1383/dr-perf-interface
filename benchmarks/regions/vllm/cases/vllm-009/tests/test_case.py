"""Bounded correctness and reachability test for vllm-009."""
from driver import run

TARGET = "vllm-009"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
