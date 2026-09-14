"""Bounded correctness and reachability test for vllm-061."""
from driver import run

TARGET = "vllm-061"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
