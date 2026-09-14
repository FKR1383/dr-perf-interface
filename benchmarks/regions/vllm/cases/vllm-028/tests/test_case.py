"""Bounded correctness and reachability test for vllm-028."""
from driver import run

TARGET = "vllm-028"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
