"""Bounded correctness and reachability test for vllm-023."""
from driver import run

TARGET = "vllm-023"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
