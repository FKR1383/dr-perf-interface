"""Bounded correctness and reachability test for vllm-003."""
from driver import run

TARGET = "vllm-003"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    run(TARGET)
