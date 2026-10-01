"""Bounded correctness and reachability test for vllm-051."""
from driver import run

TARGET = "vllm-051"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
