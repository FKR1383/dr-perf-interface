#!/usr/bin/env python3
"""Differential check of the CSV candidate; generated samples are valid CSV."""
import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import random
import sys
import types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    marker = types.ModuleType('perfmark')
    @contextlib.contextmanager
    def region(*args, **kwargs):
        yield
    marker.region = region
    sys.modules['perfmark'] = marker
    modules = []
    for name, path in [('baseline', args.baseline), ('candidate', args.candidate)]:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    rng = random.Random(17)
    differences, checked = [], 0
    for delimiter in [',', ';', ':', '|', '\t']:
        for quote in ['"', "'"]:
            for ending in ['\n', '\r\n', '\r']:
                for quoting in [csv.QUOTE_MINIMAL, csv.QUOTE_ALL]:
                    for _ in range(10):
                        stream = io.StringIO(newline='')
                        writer = csv.writer(stream, delimiter=delimiter, quotechar=quote,
                                            lineterminator=ending, quoting=quoting)
                        for _ in range(3):
                            writer.writerow([rng.choice(['alpha', 'bravo', 'x,y', 'a"b', "p'q", ' ', 'a\nb', 'a\rb']) for _ in range(3)])
                        sample = stream.getvalue()
                        results = [m.Sniffer()._guess_quote_and_delimiter(sample, None) for m in modules]
                        checked += 1
                        if results[0] != results[1]:
                            differences.append({'sample': sample, 'before': results[0], 'after': results[1]})
    result = {'checked': checked, 'different': len(differences), 'examples': differences[:10],
              'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checked': checked, 'different': len(differences)}))
    return int(bool(differences))


if __name__ == '__main__':
    raise SystemExit(main())
