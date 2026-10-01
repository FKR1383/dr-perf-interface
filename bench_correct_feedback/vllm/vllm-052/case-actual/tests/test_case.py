"""Bounded correctness and reachability test for vllm-052."""
from driver import run

TARGET = "vllm-052"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
