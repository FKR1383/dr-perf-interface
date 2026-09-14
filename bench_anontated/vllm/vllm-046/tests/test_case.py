"""Bounded correctness and reachability test for vllm-046."""
from driver import run

TARGET = "vllm-046"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
