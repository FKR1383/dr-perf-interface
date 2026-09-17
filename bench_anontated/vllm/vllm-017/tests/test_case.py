"""Bounded correctness and reachability test for vllm-017."""
from driver import run

TARGET = "vllm-017"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
