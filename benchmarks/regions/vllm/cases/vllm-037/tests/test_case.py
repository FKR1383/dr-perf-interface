"""Bounded correctness and reachability test for vllm-037."""
from driver import run

TARGET = "vllm-037"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
