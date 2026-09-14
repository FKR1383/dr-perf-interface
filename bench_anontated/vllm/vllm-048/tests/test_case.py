"""Bounded correctness and reachability test for vllm-048."""
from driver import run

TARGET = "vllm-048"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
