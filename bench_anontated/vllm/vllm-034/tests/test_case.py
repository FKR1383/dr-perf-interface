"""Bounded correctness and reachability test for vllm-034."""
from driver import run

TARGET = "vllm-034"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
