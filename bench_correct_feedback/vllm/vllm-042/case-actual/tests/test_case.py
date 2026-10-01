"""Bounded correctness and reachability test for vllm-042."""
from driver import run

TARGET = "vllm-042"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
