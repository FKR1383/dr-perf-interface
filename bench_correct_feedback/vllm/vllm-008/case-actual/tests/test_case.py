"""Bounded correctness and reachability test for vllm-008."""
from driver import run

TARGET = "vllm-008"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
