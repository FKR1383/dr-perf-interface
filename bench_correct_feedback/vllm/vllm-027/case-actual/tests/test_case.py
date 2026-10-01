"""Bounded correctness and reachability test for vllm-027."""
from driver import run

TARGET = "vllm-027"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
