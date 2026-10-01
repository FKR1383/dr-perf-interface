"""Bounded correctness and reachability test for vllm-035."""
from driver import run

TARGET = "vllm-035"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
