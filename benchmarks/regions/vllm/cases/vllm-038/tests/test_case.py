"""Bounded correctness and reachability test for vllm-038."""
from driver import run

TARGET = "vllm-038"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
