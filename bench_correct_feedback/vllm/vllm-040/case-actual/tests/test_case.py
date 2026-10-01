"""Bounded correctness and reachability test for vllm-040."""
from driver import run

TARGET = "vllm-040"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
