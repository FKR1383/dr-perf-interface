"""Bounded correctness and reachability test for vllm-030."""
from driver import run

TARGET = "vllm-030"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
