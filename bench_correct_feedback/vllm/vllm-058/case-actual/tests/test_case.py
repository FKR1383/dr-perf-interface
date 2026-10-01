"""Bounded correctness and reachability test for vllm-058."""
from driver import run

TARGET = "vllm-058"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
