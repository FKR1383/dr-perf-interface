"""Bounded correctness and reachability test for vllm-049."""
from driver import run

TARGET = "vllm-049"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
