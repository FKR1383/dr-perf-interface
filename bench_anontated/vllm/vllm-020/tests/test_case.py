"""Bounded correctness and reachability test for vllm-020."""
from driver import run

TARGET = "vllm-020"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
