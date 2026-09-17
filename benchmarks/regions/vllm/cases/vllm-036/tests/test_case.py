"""Bounded correctness and reachability test for vllm-036."""
from driver import run

TARGET = "vllm-036"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
