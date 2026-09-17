"""Bounded correctness and reachability test for vllm-025."""
from driver import run

TARGET = "vllm-025"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
