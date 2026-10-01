"""Bounded correctness and reachability test for vllm-041."""
from driver import run

TARGET = "vllm-041"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
