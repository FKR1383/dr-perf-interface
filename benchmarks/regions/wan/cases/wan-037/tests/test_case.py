"""Correctness and marker-reachability test for wan-037."""
import argparse
from marker_probe import Probe

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
probe = Probe()
from helper import run
run("wan-037", args.source_root)
probe.finish("wan-037")
