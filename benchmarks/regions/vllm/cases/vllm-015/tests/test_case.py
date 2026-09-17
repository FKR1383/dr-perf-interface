"""Bounded correctness and reachability test for vllm-015."""
from driver import run

TARGET = "vllm-015"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
