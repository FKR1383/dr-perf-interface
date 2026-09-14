"""Bounded correctness and reachability test for vllm-057."""
from driver import run

TARGET = "vllm-057"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
