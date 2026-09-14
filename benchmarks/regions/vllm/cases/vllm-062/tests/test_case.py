"""Bounded correctness and reachability test for vllm-062."""
from driver import run

TARGET = "vllm-062"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
