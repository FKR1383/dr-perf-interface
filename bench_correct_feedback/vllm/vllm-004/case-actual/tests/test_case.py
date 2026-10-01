"""Bounded correctness and reachability test for vllm-004."""
from driver import run

TARGET = "vllm-004"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
