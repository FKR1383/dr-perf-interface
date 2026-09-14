"""Bounded correctness and reachability test for vllm-005."""
from driver import run

TARGET = "vllm-005"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
