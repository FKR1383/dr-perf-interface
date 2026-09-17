"""Bounded correctness and reachability test for vllm-063."""
from driver import run

TARGET = "vllm-063"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
