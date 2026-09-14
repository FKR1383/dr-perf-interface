"""Bounded correctness and reachability test for vllm-064."""
from driver import run

TARGET = "vllm-064"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
