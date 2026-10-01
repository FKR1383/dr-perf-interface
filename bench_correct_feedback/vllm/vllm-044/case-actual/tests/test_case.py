"""Bounded correctness and reachability test for vllm-044."""
from driver import run

TARGET = "vllm-044"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
