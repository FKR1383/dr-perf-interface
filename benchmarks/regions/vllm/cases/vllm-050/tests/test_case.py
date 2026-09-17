"""Bounded correctness and reachability test for vllm-050."""
from driver import run

TARGET = "vllm-050"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
