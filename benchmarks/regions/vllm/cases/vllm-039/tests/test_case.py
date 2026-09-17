"""Bounded correctness and reachability test for vllm-039."""
from driver import run

TARGET = "vllm-039"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
