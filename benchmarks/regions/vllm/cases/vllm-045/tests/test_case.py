"""Bounded correctness and reachability test for vllm-045."""
from driver import run

TARGET = "vllm-045"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
