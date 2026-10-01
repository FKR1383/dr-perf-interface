"""Bounded correctness and reachability test for vllm-010."""
from driver import run

TARGET = "vllm-010"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
