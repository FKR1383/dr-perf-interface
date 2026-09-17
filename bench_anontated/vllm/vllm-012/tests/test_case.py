"""Bounded correctness and reachability test for vllm-012."""
from driver import run

TARGET = "vllm-012"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
