"""Bounded correctness and reachability test for vllm-060."""
from driver import run

TARGET = "vllm-060"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
