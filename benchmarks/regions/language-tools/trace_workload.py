#!/usr/bin/env python3
"""Run one shared semantic workload for coverage-guided candidate selection."""
import importlib.util
import pathlib
import sys

path=pathlib.Path(__file__).parent/"test-support"/"workloads.py"
spec=importlib.util.spec_from_file_location("lt_workloads",path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
run=module.run

run(sys.argv[1])
