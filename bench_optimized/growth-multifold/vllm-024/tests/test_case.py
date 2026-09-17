"""Bounded correctness and reachability test for vllm-024."""
from growth_driver import main

TARGET = "vllm-024"
assert TARGET.startswith("vllm-")

if __name__ == "__main__":
    main()
