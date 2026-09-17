"""Bounded correctness and reachability test for vllm-054."""
from driver import run

TARGET = "vllm-054"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
