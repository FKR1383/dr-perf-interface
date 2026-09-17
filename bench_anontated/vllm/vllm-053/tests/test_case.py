"""Bounded correctness and reachability test for vllm-053."""
from driver import run

TARGET = "vllm-053"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
