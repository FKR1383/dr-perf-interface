"""Bounded correctness and reachability test for vllm-014."""
from driver import run

TARGET = "vllm-014"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
