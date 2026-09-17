import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import bench
from evaluator.score import compare
from adapters.prepare import NeutralDriver
import ast


def claim(id='one'):
    return {'id':id,'region':'work','expression':'len(items)','evidence':'Independent input change and source loop.'}


def submission(round, correct):
    return {'round':round,'claims':[claim()], 'judgments':{
        'one':{'accepted':correct,'supports':['f1'] if correct else [],'reason':'Reviewed fixture.'}}}


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.answers = {'case':{'factors':[{'id':'f1'}]}}
        self.base = {'case':'case','family':'family','seed':0,'model':'test-model','budget':3,
                     'condition':'timing','rounds':[submission(0,False),submission(1,False)]}

    def test_paired_difference_and_unsupported_claim(self):
        treatment = copy.deepcopy(self.base)
        treatment['condition'] = 'drperf'
        treatment['rounds'][1] = submission(1,True)
        report = compare([self.base,treatment],self.answers)
        self.assertEqual(report['paired_accuracy_delta'],1)
        self.assertEqual(report['drperf_wins'],1)
        treatment['rounds'][1]['claims'].append(claim('guess'))
        treatment['rounds'][1]['judgments']['guess'] = {'accepted':False,'supports':[], 'reason':'Unsupported extra dependency.'}
        report = compare([self.base,treatment],self.answers)
        self.assertEqual(report['paired_accuracy_delta'],0)
        self.assertEqual(report['conditions']['drperf']['mean_recall'],1)
        self.assertEqual(report['conditions']['drperf']['mean_precision'],0.5)

    def test_missing_or_duplicate_pairs_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete pairs'):
            compare([self.base],self.answers)
        with self.assertRaisesRegex(ValueError,'duplicate session'):
            compare([self.base,self.base],self.answers)

    def test_input_access_tracks_cannot_be_pooled(self):
        treatment = copy.deepcopy(self.base)
        treatment.update(condition='drperf', track='small-to-large')
        with self.assertRaisesRegex(ValueError, 'score each track separately'):
            compare([self.base,treatment], self.answers)
        baseline = copy.deepcopy(self.base)
        baseline['track'] = 'small-to-large'
        self.assertEqual(compare([baseline,treatment], self.answers)['track'], 'small-to-large')

    def test_losing_correct_answer_is_not_final_accuracy(self):
        treatment = copy.deepcopy(self.base)
        treatment['condition']='drperf'
        treatment['rounds']=[submission(0,False),submission(1,True),submission(2,False)]
        report = compare([self.base,treatment],self.answers)
        result=report['sessions'][1]
        self.assertEqual(result['first_exact_round'],1)
        self.assertTrue(result['success_by_budget'])
        self.assertFalse(result['accuracy_at_budget'])


class EvidenceTests(unittest.TestCase):
    def test_all_cases_and_imported_assets_have_provenance(self):
        cases=bench.read(ROOT/'catalog.json')['cases']
        self.assertEqual(len(cases),29)
        self.assertEqual(len(cases),len(set(cases)))
        for case in cases:
            ref=ROOT/'cases'/case/'reference'
            provenance=bench.read(ref/'provenance.json')
            self.assertEqual(hashlib.sha256((ref/'record.md').read_bytes()).hexdigest(),provenance['record']['sha256'])
            for item in provenance['assets']:
                asset=ref/'assets'/item['archive_path']
                self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(),item['sha256'])

    def test_candidates_are_not_promoted_to_ground_truth(self):
        inventory=bench.read(ROOT/'evaluator/region-candidates.json')
        self.assertEqual(inventory['scored_cases'],0)
        self.assertTrue(all(c['status']=='needs-review' for c in inventory['candidates']))
        for path, sha in inventory['report_hashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/'evaluator/region-reports'/path).read_bytes()).hexdigest(),sha)

    def test_neutral_sqlglot_driver_removes_solved_expression(self):
        original=(ROOT/'cases/sqlglot/reference/assets/oss/run_sqlglot.py').read_text()
        neutral=ast.unparse(ast.fix_missing_locations(NeutralDriver().visit(ast.parse(original))))
        self.assertNotIn('n_joins_sq',neutral)
        self.assertNotIn('n * n',neutral)
        self.assertNotIn('perfmark.region',neutral)
        self.assertIn('optimize(expression, schema=schema)',neutral)


class BudgetTests(unittest.TestCase):
    def test_small_input_envelope_rejects_large_or_implicit_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            bench.write(workspace/'session.json',{'case':'sqlglot','condition':'timing',
                'track':'small-to-large', 'points_per_round':6,
                'input_envelope':{'n_joins':{'min':2,'max':32}}})
            for point in ({}, {'n_joins':64}, {'n_joins':1}, {'n_joins':True},
                          {'n_joins':'8'}, {'n_joins':8.0}, {'n_joins':8,'repeats':100}):
                bench.write(workspace/'plan.json',[point])
                with self.subTest(point=point), self.assertRaisesRegex(ValueError,'envelope'):
                    bench.measure(workspace,'timing',workspace/'plan.json',workspace/'hypothesis.json')
            self.assertFalse((workspace/'measurements').exists())

    def test_submissions_are_immutable_and_cannot_skip_round_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            bench.write(workspace/'session.json',{'case':'fixture','condition':'timing'})
            bench.write(workspace/'hypothesis.json',{'claims':[claim()]})
            with contextlib.redirect_stdout(io.StringIO()):
                bench.submit(workspace,workspace/'hypothesis.json')
            with self.assertRaisesRegex(ValueError,'already has'):
                bench.submit(workspace,workspace/'hypothesis.json')
            round_path=workspace/'measurements/round-01'
            round_path.mkdir()
            bench.write(round_path/'result.json',{'status':'running'})
            with self.assertRaisesRegex(ValueError,'finish the measurement'):
                bench.submit(workspace,workspace/'hypothesis.json')
            bench.write(round_path/'result.json',{'status':'ok'})
            with contextlib.redirect_stdout(io.StringIO()):
                bench.submit(workspace,workspace/'hypothesis.json')
            self.assertEqual(bench.read(workspace/'measurements/submissions/round-01.json')['claims'],[claim()])

    def test_failed_runs_consume_budget_and_timing_cannot_request_drperf(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            (workspace/'workload.py').write_text('raise RuntimeError("intentional workload failure")\n')
            bench.write(workspace/'session.json',{'case':'fixture','condition':'timing',
                'python':sys.executable,'env':{},'workload':'workload.py','round_budget':3,
                'points_per_round':6,'process_timeout_seconds':5})
            bench.write(workspace/'plan.json',[{}])
            bench.write(workspace/'hypothesis.json',{'claims':[]})
            args=(workspace,'timing',workspace/'plan.json',workspace/'hypothesis.json')
            with self.assertRaisesRegex(ValueError,'no drperf feedback'):
                bench.measure(workspace,'drperf',args[2],args[3])
            with contextlib.redirect_stdout(io.StringIO()):
                for _ in range(3):
                    self.assertEqual(bench.measure(*args),1)
            with self.assertRaisesRegex(ValueError,'budget exhausted'):
                bench.measure(*args)
            self.assertEqual(len(list((workspace/'measurements').glob('round-*'))),3)

    def test_invalid_drperf_trace_suppresses_feedback(self):
        sys.path.insert(0,str(ROOT.parent/'lib'))
        import runner
        with tempfile.TemporaryDirectory() as directory:
            workspace=Path(directory)
            (workspace/'workload.py').write_text('pass\n')
            bench.write(workspace/'session.json',{'case':'fixture','condition':'drperf',
                'python':sys.executable,'env':{},'workload':'workload.py','round_budget':3,
                'points_per_round':6,'process_timeout_seconds':5})
            bench.write(workspace/'plan.json',[{}])
            bench.write(workspace/'hypothesis.json',{'claims':[]})
            def overflow(cmd,out,timeout):
                Path(out).mkdir()
                bench.write(Path(out)/'run.1.json',{'drperf':{'slots_overflow':1,'max_slots':1}})
                return 0,'',['run.1.json']
            with patch.object(runner,'run',side_effect=overflow),contextlib.redirect_stdout(io.StringIO()):
                rc=bench.measure(workspace,'drperf',workspace/'plan.json',workspace/'hypothesis.json')
            self.assertEqual(rc,1)
            self.assertFalse((workspace/'measurements/round-01/feedback.txt').exists())
            result=bench.read(workspace/'measurements/round-01/result.json')
            self.assertIn('did not fit',result['points'][0]['warnings'][0])


if __name__=='__main__':
    unittest.main()
