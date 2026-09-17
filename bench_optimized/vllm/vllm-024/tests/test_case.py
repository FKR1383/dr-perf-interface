"""Bounded correctness and reachability test for vllm-024."""
from driver import run

TARGET = "vllm-024"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
