#!/usr/bin/env python3
"""Check benchmark immutability and the experiment's marked boundaries."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class NormalizeMarker(ast.NodeTransformer):
    def __init__(self, mask_body=False):
        self.mask_body = mask_body
        self.count = 0

    def visit_With(self, node):
        if len(node.items) == 1:
            call = node.items[0].context_expr
            if isinstance(call, ast.Call) and ast.unparse(call.func) == 'perfmark.region':
                self.count += 1
                call.keywords = []
                if self.mask_body:
                    node.body = [ast.Pass()]
                return node
        return self.generic_visit(node)


def normalized(path, mask_body=False):
    transform = NormalizeMarker(mask_body)
    tree = transform.visit(ast.parse(path.read_bytes()))
    if transform.count != 1:
        raise ValueError(f'expected exactly one marker in {path}; saw {transform.count}')
    return ast.dump(tree)


def replay_patch(original, expected, patch, relative):
    if original.read_bytes() == expected.read_bytes():
        return
    if not patch.is_file():
        raise ValueError('missing ' + str(patch))
    with tempfile.TemporaryDirectory(prefix='drperf-patch-replay-') as tmp:
        target = Path(tmp)/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original.read_bytes())
        subprocess.run(['git', 'apply', str(patch.resolve())], cwd=tmp,
                       check=True, capture_output=True)
        if target.read_bytes() != expected.read_bytes():
            raise ValueError('patch does not reproduce final source: ' + str(patch))


def main():
    snapshot = json.loads((ROOT/'bench_anontated/benchmark-snapshot.json').read_text())['files']
    current = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT/'benchmarks').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    errors = []
    if snapshot != current:
        errors.append('benchmark tree changed: ' + ', '.join(sorted(k for k in snapshot.keys() | current.keys() if snapshot.get(k) != current.get(k))))
    spec = importlib.util.spec_from_file_location('collection', ROOT/'benchmarks/regions/collect.py')
    collection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collection)
    checked_annotations = checked_optimizations = 0
    for manifest in sorted((ROOT/'benchmarks/regions').glob('*/cases/*/case.json')):
        data = json.loads(manifest.read_text())
        if data['language'] != 'python':
            continue
        group = manifest.relative_to(ROOT/'benchmarks/regions').parts[0]
        ann = ROOT/'bench_anontated'/group/data['id']
        source = ann/data['source']['path']
        if not source.exists():
            errors.append(f'{data["id"]}: missing annotation source')
            continue
        with tempfile.TemporaryDirectory(prefix='drperf-boundary-check-') as tmp:
            original = collection.apply(manifest, data, Path(tmp))
            if normalized(original) != normalized(source):
                errors.append(f'{data["id"]}: annotation changed source behavior or marker boundary')
            try:
                replay_patch(original, source, ann/'annotation.patch', data['source']['path'])
            except (ValueError, subprocess.CalledProcessError) as exc:
                errors.append(f'{data["id"]}: annotation patch replay failed: {exc}')
        checked_annotations += 1
        annotation_result = ann/'result.json'
        if annotation_result.exists():
            record = json.loads(annotation_result.read_text())
            if record.get('final_measurement'):
                measurement = (ann/record['final_measurement']).resolve()
                invocation = json.loads((measurement.parent/'invocation.json').read_text())
                hashes = invocation.get('source_hashes', {})
                for relative, digest in hashes.items():
                    if relative == data['source']['path'] or relative.startswith('tests/'):
                        file = ann/relative
                        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                            errors.append(f'{data["id"]}: final annotation measurement does not match {relative}')
        opt = ROOT/'bench_optimized'/group/data['id']
        result_path = opt/'result.json'
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text())
        if not result.get('accepted'):
            continue
        if normalized(source, True) != normalized(opt/data['source']['path'], True):
            errors.append(f'{data["id"]}: accepted optimization changed code outside the marker')
        try:
            replay_patch(source, opt/data['source']['path'], opt/'optimization.patch', data['source']['path'])
        except (ValueError, subprocess.CalledProcessError) as exc:
            errors.append(f'{data["id"]}: optimization patch replay failed: {exc}')
        for field, base in [('baseline_measurement', opt), ('optimized_measurement', opt)]:
            path = (base/result[field]).resolve()
            metrics = json.loads(path.read_text())
            if metrics.get('returncode') != 0 or metrics.get('validity_warnings'):
                errors.append(f'{data["id"]}: invalid {field}')
            if field == 'baseline_measurement' and not metrics.get('gate_pass'):
                errors.append(f'{data["id"]}: baseline did not pass annotation gate')
            invocation = json.loads((path.parent/'invocation.json').read_text())
            measured_case = ann if field == 'baseline_measurement' else opt
            for relative, digest in invocation.get('source_hashes', {}).items():
                if relative == data['source']['path'] or relative.startswith('tests/'):
                    file = measured_case/relative
                    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                        errors.append(f'{data["id"]}: {field} does not match {relative}')
        checked_optimizations += 1
    report = {'benchmark_unchanged': snapshot == current,
              'annotations_checked': checked_annotations,
              'accepted_optimizations_checked': checked_optimizations, 'errors': errors}
    (ROOT/'bench_anontated/audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
