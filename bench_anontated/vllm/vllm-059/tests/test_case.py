"""Bounded correctness and reachability test for vllm-059."""
from driver import run

TARGET = "vllm-059"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
