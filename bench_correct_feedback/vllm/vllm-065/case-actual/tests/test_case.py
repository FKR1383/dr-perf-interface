"""Bounded correctness and reachability test for vllm-065."""
from driver import run

TARGET = "vllm-065"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
