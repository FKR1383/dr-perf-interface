import copy
from collections import Counter
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import wait_contracts as W


def fixture(samples=((0, 0), (1, 1))):
    traces = [{'group': '0:1', 'thread': '1', 'seq': 1, 'end': 2, 'region': 'B', 'values': {}}]
    events = []
    def event(kind, start, region='', regionSeq=0, api=None, **kw):
        events.append(dict(id=str(start), group='0:1', tid=1, kind=kind, api=api or kind,
                           start=start, end=start+1, object='100', aux='0', region=region,
                           regionSeq=regionSeq, returned=True, result=0, **kw))
    event('event_create', 1)
    event('event_record', 3, 'B', 1)
    for i, (state, count) in enumerate(samples):
        seq = 3 + i*2
        traces.append(dict(group='0:1', thread='1', seq=seq, end=seq+1, region='A', values={'full': state}))
        for j in range(count):
            event('event_wait', 10+i*100+j*2, 'A', seq, 'cudaEventSynchronize')
    counts = Counter(state for state, _ in samples)
    return dict(validity={}, trace=dict(complete=True, events=traces),
                regions=[dict(id='B', states=[], calls=1, points=[dict(state=[], calls=1)]),
                         dict(id='A', states=['full'], calls=len(samples),
                              points=[dict(state=[v], calls=n) for v, n in counts.items()])],
                waits=dict(status='observed', events=events, operations=[]))


def declaration(indicator='full == 1', producer='B'):
    return dict(version=1, claims=[dict(id='test', region='A', api='cudaEventSynchronize',
                                       indicator=indicator, producer=producer)])


class WaitContracts(unittest.TestCase):
    def test_both_present_and_absent_checked(self):
        report = W.check(fixture(), declaration())
        self.assertEqual(report['status'], 'verified-observed')
        self.assertEqual(report['claims'][0]['branchCoverage'], 'both outcomes')
        self.assertEqual(report['claims'][0]['multiplicity']['constant'], '1')

    def test_always_and_never_rejected_in_opposite_directions(self):
        for expression, failure in [('True', 'unexpectedAbsence'), ('False', 'unexpectedPresence')]:
            row = W.check(fixture(), declaration(expression))['claims'][0]
            self.assertEqual(row['status'], 'invalid')
            self.assertEqual(row[failure], 1)
            self.assertEqual(row['counterexamples'][0]['kind'], failure)

    def test_reversed_guard_catches_both_directions(self):
        row = W.check(fixture(), declaration('full == 0'))['claims'][0]
        self.assertEqual((row['unexpectedPresence'], row['unexpectedAbsence']), (1, 1))

    def test_per_invocation_not_state_average(self):
        row = W.check(fixture(((1, 0), (1, 2))), declaration())['claims'][0]
        self.assertEqual(row['unexpectedAbsence'], 1)
        self.assertEqual(row['status'], 'invalid')

    def test_no_declaration_leaves_detected_sync_unexplained(self):
        report = W.check(fixture(), dict(version=1, claims=[]))
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['unexplained'][0]['term'], 'unexplained(Wait[B])')

    def test_producer_must_have_evidence_and_cannot_be_filtered_out(self):
        report = W.check(fixture(), declaration(producer='wrong'))
        self.assertEqual(report['status'], 'invalid')
        self.assertEqual(report['claims'][0]['producerMismatches'], 1)
        self.assertEqual(report['coverage']['unexplainedOperations'], 1)

    def test_unknown_owner_preserves_obligation(self):
        model = fixture()
        model['waits']['events'] = [e for e in model['waits']['events'] if e['kind'] != 'event_record']
        report = W.check(model, declaration())
        self.assertEqual(report['claims'][0]['indicatorStatus'], 'verified-observed')
        self.assertEqual(report['claims'][0]['producerStatus'], 'unverified')
        self.assertEqual(report['unexplained'][0]['term'], 'unexplained(Wait[?])')

    def test_count_fitted_separately_from_indicator(self):
        row = W.check(fixture(((0, 0), (1, 2))), declaration())['claims'][0]
        self.assertEqual(row['status'], 'verified-observed')
        self.assertEqual(row['multiplicity']['constant'], '2')

    def test_failed_sync_is_observed_but_not_verified_completion(self):
        model = fixture(); model['waits']['events'][-1]['result'] = 1
        report = W.check(model, declaration())
        self.assertEqual(report['claims'][0]['indicatorStatus'], 'verified-observed')
        self.assertEqual(report['claims'][0]['producerStatus'], 'unverified')

    def test_partial_capture_cannot_verify_absence(self):
        for change in ('waits', 'trace'):
            model = fixture()
            if change == 'waits': model['waits']['status'] = 'partial'
            else: model['trace']['complete'] = False
            report = W.check(model, declaration())
            self.assertEqual(report['status'], 'unverified')
            self.assertFalse(report['claims'])

    def test_empty_or_corrupt_trace_cannot_prove_no_wait(self):
        model = fixture(); model['trace']['events'].pop()
        with self.assertRaises(ValueError): W.check(model, declaration())

    def test_no_active_samples_cannot_verify_target(self):
        row = W.check(fixture(((0, 0),)), declaration())['claims'][0]
        self.assertEqual(row['indicatorStatus'], 'verified-observed')
        self.assertEqual(row['producerStatus'], 'unverified')
        self.assertEqual(row['branchCoverage'], 'only absent')

    def test_unsupported_queries_are_not_treated_as_observed_zero(self):
        d = declaration(); d['claims'][0]['api'] = 'cudaEventQuery'
        with self.assertRaises(ValueError): W.check(fixture(), d)

    def test_duplicate_claims_cannot_double_explain_an_operation(self):
        d = declaration(); other = dict(d['claims'][0], id='other'); d['claims'].append(other)
        with self.assertRaises(ValueError): W.check(fixture(), d)

    def test_unsafe_or_unknown_expressions_rejected_even_in_dead_branch(self):
        for text in ['f()', 'x.y', 'full[0]', '__import__("os")', 'True or missing', '2', '1 // 0']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                W.check(fixture(), declaration(text))

    def test_unrelated_syncs_are_not_silently_covered(self):
        model = fixture(); extra = dict(model['waits']['events'][-1], id='1000', start=1000,
                                        end=1001, api='pthread_mutex_lock', kind='lock')
        model['waits']['events'].append(extra)
        report = W.check(model, declaration())
        self.assertEqual(report['claims'][0]['status'], 'verified-observed')
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['unexplained'][0]['api'], 'pthread_mutex_lock')

    def test_missing_records_cannot_be_hidden_by_observed_status(self):
        model = fixture()
        model['provenance'] = {'runs': [{'measurement': {'pid': 1, 'wait_records': 3}}]}
        model['waits']['events'].pop()
        self.assertEqual(W.check(model, declaration())['status'], 'unverified')

    def test_unknown_selector_cannot_silently_filter_observations(self):
        d = declaration(); d['claims'][0]['onlyWhen'] = 'False'
        with self.assertRaises(ValueError): W.check(fixture(), d)

    def test_supplied_producer_labels_are_not_trusted(self):
        model = fixture(); model['waits']['operations'] = [dict(model['waits']['events'][-1], producers=['fake'])]
        self.assertEqual(W.check(model, declaration())['status'], 'verified-observed')


if __name__ == '__main__': unittest.main()
