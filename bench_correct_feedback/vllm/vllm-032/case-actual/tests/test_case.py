"""Bounded correctness and reachability test for vllm-032."""
from driver import run

TARGET = "vllm-032"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
