"""Bounded correctness and reachability test for vllm-055."""
from driver import run

TARGET = "vllm-055"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
