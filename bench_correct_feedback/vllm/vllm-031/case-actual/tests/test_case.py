"""Bounded correctness and reachability test for vllm-031."""
from driver import run

TARGET = "vllm-031"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
