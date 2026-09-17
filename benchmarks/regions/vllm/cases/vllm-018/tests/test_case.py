"""Bounded correctness and reachability test for vllm-018."""
from driver import run

TARGET = "vllm-018"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
