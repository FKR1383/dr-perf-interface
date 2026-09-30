"""Exact marker exclusion preserves wrapper work and ignores calibration."""
from collections import Counter
import copy
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import derive
import explorer
import markers
import runner


class Capture:
    slots = {0: ('libperfmark.so', 'perfmark_begin', 0),
             1: ('python', 'inside_wrapper', 1),
             2: ('python', 'outside_wrapper', 2),
             3: ('app', 'work', 3), 4: ('python', 'loop', 4)}
    def __init__(self):
        self.keys, self.records, self.seq = {}, [], 0
        self.identities = {}

    def call(self, name, value, vector, body=None, run=0):
        state = [('n', value)]
        identity = run, name, value
        if identity not in self.identities:
            key = run, len(self.keys)
            self.identities[identity] = key
            self.keys[key] = {'region': name, 'states': state, 'count': 0, 'vec': {}, 'root': ''}
        row = self.keys[self.identities[identity]]
        row['count'] += 1
        vec = Counter(row['vec']); vec.update(vector); row['vec'] = dict(vec)
        self.seq += 1
        record = {'run': run, 'pid': 1, 'tid': 1, 'region': name, 'state': dict(state), 'nk': 1, 'seq': self.seq}
        self.records.append(record)
        if body:
            body()
        self.seq += 1
        record['seq_end'] = self.seq

    def calibrate(self, inside=20, outside=3, run=0):
        self.call(markers.CALIB+'_loop', 0, {0: 10, 1: inside, 4: 30}, run=run)
        self.call(markers.CALIB+'_outer', 0, {0: 50, 1: inside, 2: 4*outside, 4: 30},
                  lambda: [self.call(markers.CALIB, 0, {0: 10, 1: inside}, run=run) for _ in range(4)], run=run)


class MarkerAccounting(unittest.TestCase):
    def test_legacy_calibration_cannot_change_application_formula(self):
        cap = Capture(); cap.calibrate(inside=2000, outside=3000)
        for n in (0, 1, 3, 7, 12):
            cap.call('parent', n, {0: 10+10*n, 1: 20, 2: 3*n, 3: 100*n+7},
                     lambda: [cap.call('child', n, {0: 10, 1: 20, 3: 50*n+2}) for _ in range(n)])
        saved = copy.deepcopy(cap.keys)
        adjusted, accounting = markers.adjust(cap.keys, cap.slots, cap.records)
        vecs, _ = derive.per_trigger(derive.per_state(adjusted, 'parent')[0])
        fit = derive.derive(vecs, cap.slots, split=False)[0]
        self.assertAlmostEqual(fit.a[0], 103)
        self.assertAlmostEqual(fit.c, 27)
        for state, vec in vecs.items():
            self.assertEqual(sum(vec.values()), 103*state[0]+27)
            self.assertEqual(accounting[('parent', state)]['exactBlocks'], 10+10*state[0])
        self.assertEqual(cap.keys, saved)
        without = {k:r for k,r in cap.keys.items() if not r['region'].startswith(markers.CALIB)}
        no_calibration, _ = markers.adjust(without, cap.slots, [])
        self.assertEqual(derive.per_state(adjusted, 'parent'),
                         derive.per_state(no_calibration, 'parent'))

    def test_tiny_region_preserves_shared_interpreter_blocks(self):
        cap = Capture(); cap.calibrate()
        cap.call('tiny', 1, {0: 10, 1: 2, 3: 7})
        for errors in ([], ['truncated']):
            adjusted, accounting = markers.adjust(cap.keys, cap.slots, cap.records, errors)
            row = next(r for r in adjusted.values() if r['region'] == 'tiny')
            self.assertEqual(row['vec'], {1: 2, 3: 7})
            info = markers.metadata('tiny', ['n'], accounting)
            self.assertEqual(info['method'], 'marker-module exclusion only')
            self.assertNotIn('unmatchedEstimate', info['points'][0])

    def test_nonlinear_wrapper_work_is_not_hidden(self):
        cap = Capture(); cap.calibrate()
        for n in (0, 1, 3, 7, 12):
            cap.call('parent', n, {0: 10, 1: 20, 2: 300*n*n, 3: 100*n+7})
        adjusted, _ = markers.adjust(cap.keys, cap.slots, cap.records)
        vecs, _ = derive.per_trigger(derive.per_state(adjusted, 'parent')[0])
        fit = derive.derive(vecs, cap.slots, split=False)[0]
        self.assertGreater(fit.n_irr, 0)
        self.assertAlmostEqual(fit.a[0], 100)

    def test_shared_state_root_buckets_preserve_measured_work(self):
        cap = Capture()
        cap.call('parent', 1, {0: 10, 1: 20, 2: 12, 3: 7})
        key = cap.identities[(0, 'parent', 1)]
        cap.keys[(0, 1000)] = dict(cap.keys[key], root='idle', vec={0: 10, 1: 20, 3: 7})
        adjusted, accounting = markers.adjust(cap.keys, cap.slots, cap.records)
        own, _, _ = derive.per_state(adjusted, 'parent')
        self.assertEqual(own[(1,)], ({1: 40, 2: 12, 3: 14}, 2))
        self.assertEqual(accounting[('parent', (1,))]['exactBlocks'], 20)

    def test_marker_identity_includes_binding_but_not_application_symbols(self):
        self.assertTrue(markers.is_marker(('libperfmark.so', 'anything')))
        self.assertTrue(markers.is_marker(('_perfmark.cpython-311-x86_64-linux-gnu.so', 'Region_enter')))
        self.assertFalse(markers.is_marker(('libpython.so', 'work')))

    def test_automatic_calibration_is_disabled(self):
        with patch.dict(os.environ, {'PERFMARK_CALIBRATE': '1'}):
            self.assertNotIn('PERFMARK_CALIBRATE', runner.build_env())
        self.assertEqual(runner.calibration({}), (0, 0))
        self.assertEqual(runner.marker_cost({}), (0, 0))


class PythonMarkers(unittest.TestCase):
    def test_real_nested_python_wrapper_profiles(self):
        self.check_python(False)

    def test_real_nested_ctypes_wrapper_profiles(self):
        self.check_python(True)

    def check_python(self, ctypes):
        with tempfile.TemporaryDirectory(prefix='markers-', dir=ROOT/'out') as temporary:
            folder = Path(temporary)
            app = folder/'app.py'
            app.write_text('''import perfmark
def leaf(n):
    with perfmark.region("leaf", n=n):
        with perfmark.region("perf.pcv"):
            scratch = sum(i*i for i in range(100*n))
        total = 0
        for i in range(100*n): total += i
    return total
def middle(n):
    with perfmark.region("middle", n=n):
        for i in range(n): leaf(n)
for n in (0,1,2,4,8):
    with perfmark.region("outer", n=n): middle(n)
''')
            with patch.dict(os.environ, {'DRPERF_FOLLOW_THREADS':'0', 'PERFMARK_NO_EXT': '1' if ctypes else '', 'PERFMARK_CALIBRATE': '1'}):
                rc, log, files = runner.run([sys.executable, str(app)], str(folder/'raw'), timeout=90)
            self.assertEqual(rc, 0, log); self.assertTrue(files, log)
            model = explorer.build_model(folder/'raw', discover=False)
            self.assertEqual(model['composition']['status'], 'observed')
            regions = {r['id']: r for r in model['regions']}
            self.assertEqual(set(regions), {'outer', 'middle', 'leaf'})
            runs = explorer.load_raw_runs(folder/'raw')
            raw_keys, _ = runner.blocks_of_set(runs)
            self.assertFalse(any(r['region'].startswith(markers.CALIB) for r in raw_keys.values()))
            self.assertTrue(any(r['region'] == 'perf.pcv' for r in raw_keys.values()))
            self.assertFalse(any(e['child'] == 'perf.pcv' for r in model['composition']['regions']
                                 for e in r['children']))
            for name, region in regions.items():
                self.assertTrue(all(p['observed'] >= 0 for p in region['points']))
                # Current clients exclude marker modules during execution;
                # legacy profiles still use exact block subtraction on export.
                self.assertTrue(all(p['recorded'] == p['observed'] for p in region['points']))
                self.assertEqual(region['markerAdjustment']['method'], 'marker-module exclusion only')
                self.assertFalse(any('calibration' in d.lower() for d in region['diagnostics']))
                for point, adjustment in zip(region['points'], region['markerAdjustment']['points']):
                    self.assertAlmostEqual(point['recorded'] - point['observed'], adjustment['exactBlocks'])
                for fit in region['regimes']:
                    for group in fit['attribution']['coefficients'] + [fit['attribution']['constant'], fit['attribution']['unexplained']]:
                        self.assertFalse(any(markers.is_marker((r['module'], r['function'])) for r in group))
            self.assertTrue(all(p['directChildCalls'] == 1 for p in regions['outer']['markerAdjustment']['points']))
            self.assertTrue(all(p['directChildCalls'] == p['state'][0] for p in regions['middle']['markerAdjustment']['points']))
            self.assertTrue(all(p['directChildCalls'] == 1 for p in regions['leaf']['markerAdjustment']['points']))


if __name__ == '__main__':
    unittest.main()
