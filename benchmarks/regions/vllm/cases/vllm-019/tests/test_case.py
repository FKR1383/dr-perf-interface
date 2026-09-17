"""Bounded correctness and reachability test for vllm-019."""
from driver import run

TARGET = "vllm-019"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
