"""Bounded correctness and reachability test for vllm-047."""
from driver import run

TARGET = "vllm-047"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
