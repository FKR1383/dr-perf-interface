"""Bounded correctness and reachability test for vllm-067."""
from driver import run

TARGET = "vllm-067"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
