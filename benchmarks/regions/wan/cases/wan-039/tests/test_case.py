"""Correctness and marker-reachability test for wan-039."""
import argparse
from marker_probe import Probe

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
probe = Probe()
from helper import run
run("wan-039", args.source_root)
probe.finish("wan-039")
