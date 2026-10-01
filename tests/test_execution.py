"""Region graphs preserve execution order without manufacturing dependencies."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import execution
from test_composition import Fixture


def model(f):
    return {'regions': f.model(), 'trace': {'complete': True, 'events': f.events},
            'validity': {'errors': [], 'traceErrors': []}}


class ExecutionGraph(unittest.TestCase):
    def test_nesting_and_adjacent_order_are_distinct(self):
        f = Fixture()
        f.call('outer', {}, lambda: (f.call('a', {}), f.call('b', {})))
        g = execution.build(model(f))
        edges = {(e['kind'], e['source'], e['target']) for e in g['edges']}
        self.assertEqual(edges, {('contains', 'outer', 'a'), ('contains', 'outer', 'b'),
                                 ('sequence', 'a', 'b')})
        self.assertEqual(next(e for e in g['edges'] if e['kind'] == 'sequence')['context'], 'outer')

    def test_no_order_across_execution_contexts(self):
        f = Fixture()
        f.call('a', {}, thread='1'); f.call('b', {}, thread='2')
        f.call('c', {}, group='1:2'); f.call('d', {}, thread='1')
        g = execution.build(model(f))
        self.assertEqual([(e['source'], e['target']) for e in g['edges']], [('a', 'd')])
        self.assertEqual({n['id'] for n in g['nodes']}, {'a', 'b', 'c', 'd'})

    def test_zero_call_parents_in_count_fit(self):
        f = Fixture()
        for n in (0, 1, 3):
            f.call('p', {'n': n}, lambda: [f.call('c', {}) for _ in range(n)])
        g = execution.build(model(f))
        edge = next(e for e in g['edges'] if e['kind'] == 'contains')
        self.assertEqual(edge['invocationsChecked'], 3)
        self.assertEqual(edge['perInvocation']['coefficients'], ['1'])
        self.assertEqual(edge['perInvocation']['constant'], '0')
        # Repeat count max(n-1,0) is not affine on these states.
        self.assertIsNone(next(e for e in g['edges'] if e['kind'] == 'sequence')['perInvocation'])

    def wait_model(self):
        f = Fixture()
        f.call('producer', {}, thread='1')
        f.call('consumer', {}, thread='2')
        m = model(f)
        producer = dict(f.events[0], id='publish', regionSeq=1)
        operation = dict(f.events[1], id='wait', api='sem_wait', producers=['publish'],
                         dependency='matched-completion', regionSeq=3)
        m['waits'] = {'status': 'observed', 'events': [producer], 'operations': [operation]}
        return m

    def test_internal_synchronization_does_not_make_a_self_wait(self):
        f = Fixture()
        f.call('same', {}, thread='1'); f.call('same', {}, thread='2')
        m = model(f)
        m['waits'] = {'status': 'observed',
                     'events': [dict(f.events[0], id='pub'), dict(f.events[1], id='op')],
                     'operations': [dict(f.events[1], id='op', api='sem_wait',
                                         producers=['pub'], dependency='matched')]}
        m['eventModel'] = {'edges': [dict(waited='op', publication='pub', event='1',
                                         generation='1', status='ordered')]}
        g = execution.build(m)
        self.assertFalse(any(e['kind'] == 'wait' for e in g['edges']))
        self.assertEqual(g['nodes'][0]['waitOperations']['sem_wait'], 1)
        self.assertNotIn('<unresolved>', g['nodes'][0]['waitOperations'])
        self.assertEqual(len(m['waits']['operations']), 1)

    def test_root_retains_external_wait_producer_without_thread_nodes(self):
        g = execution.build(self.wait_model(), 'consumer')
        self.assertEqual([(e['kind'], e['source'], e['target']) for e in g['edges']],
                         [('wait', 'consumer', 'producer')])
        nodes = {n['id']: n for n in g['nodes']}
        self.assertTrue(nodes['producer']['dependencyOnly'])
        self.assertFalse(nodes['consumer']['dependencyOnly'])
        self.assertEqual(g['edges'][0]['evidence'][0]['producer'], 'publish')

    def test_partial_or_missing_producer_does_not_invent_edge(self):
        for partial in (True, False):
            m = self.wait_model()
            if partial: m['waits']['status'] = 'partial'
            else: m['waits']['events'] = []
            g = execution.build(m, 'consumer')
            self.assertFalse(g['edges'])
            self.assertEqual(g['nodes'][0]['waitOperations']['<unresolved>'], 1)

    def test_declared_events_include_ordered_and_violated_claims_separately(self):
        m = self.wait_model()
        consumer = m['waits']['operations'][0]
        m['waits']['events'].append(consumer)
        m['waits']['operations'] = []
        m['eventModel'] = {'status': 'violation', 'probe': True, 'violations': [{}],
            'edges': [dict(waited='wait', publication='publish', event='1', generation='1', status=status)
                      for status in ['ordered', 'violation']]}
        g = execution.build(m, 'consumer')
        self.assertTrue(g['declaredEventsIncluded'])
        self.assertEqual(g['eventChecks']['violations'], 1)
        self.assertTrue(g['eventChecks']['probe'])
        self.assertEqual({e['eventStatus'] for e in g['edges']}, {'ordered', 'violation'})
        for e in g['edges']:
            self.assertEqual((e['source'],e['target']), ('consumer','producer'))
            self.assertEqual(e['perInvocation']['constant'], '1')
            self.assertEqual(e['origin'], 'declared-event')
        self.assertIn('#c62828', execution.dot(g))
        self.assertIn('declared wait: violation', execution.dot(g))
        # Missing publishers never produce an invented graph endpoint.
        m['waits']['events'] = [consumer]
        self.assertFalse(execution.build(m)['edges'])
        m['waits']['status'] = 'partial'
        self.assertFalse(execution.build(m)['edges'])

    def test_parent_declaration_survives_unresolved_child_primitive(self):
        f=Fixture()
        f.call('C',{},thread='2')
        f.call('A',{},lambda:f.call('B',{},thread='1'),thread='1')
        m=model(f)
        calls={t['region']:t for t in f.events}
        pub=dict(calls['C'],id='publication')
        waited=dict(calls['A'],id='waited')
        primitive=dict(calls['B'],id='primitive',api='sem_wait',producers=[],dependency='unresolved')
        m['waits']={'status':'observed','events':[pub,waited], 'operations':[primitive]}
        m['eventModel']={'edges':[dict(waited='waited',publication='publication',event='1',generation='1',status='ordered')]}
        g=execution.build(m)
        self.assertEqual([(e['source'],e['target']) for e in g['edges'] if e['kind']=='wait'],[('A','C')])
        self.assertEqual(next(n for n in g['nodes'] if n['id']=='B')['waitOperations']['<unresolved>'],1)

    def test_root_selection_includes_descendants_only(self):
        f = Fixture()
        f.call('other', {})
        f.call('p', {}, lambda: f.call('c', {}, lambda: f.call('g', {})))
        g = execution.build(model(f), 'p')
        self.assertEqual({n['id'] for n in g['nodes']}, {'p', 'c', 'g'})
        with self.assertRaises(ValueError): execution.build(model(f), 'absent')

    def test_depth_limited_view_retains_direct_children_and_notes_hidden_work(self):
        f = Fixture()
        f.call('p', {}, lambda: f.call('c', {}, lambda: f.call('g', {})))
        g = execution.build(model(f), 'p', max_depth=1)
        nodes = {n['id']: n for n in g['nodes']}
        self.assertEqual(set(nodes), {'p', 'c'})
        self.assertEqual(nodes['c']['hiddenChildren'], ['g'])
        self.assertTrue(all(e['source'] in nodes and e['target'] in nodes for e in g['edges']))

    def test_incomplete_or_invalid_trace_is_not_graphed(self):
        f = Fixture(); f.call('p', {})
        for mode in ('partial', 'missing', 'error'):
            m = model(f)
            if mode == 'partial': m['trace']['complete'] = False
            elif mode == 'missing': m['trace']['events'] = []
            else: m['validity']['errors'] = ['overflow']
            self.assertEqual(execution.build(m)['status'], 'unavailable')

    def test_integer_display_keeps_underlying_fit(self):
        f = Fixture(); f.call('p', {'n': 1})
        m = model(f); m['regions'][0]['regimes'][0]['coefficients'] = [1.75]
        g = execution.build(m)
        self.assertEqual(g['nodes'][0]['ownFits'][0]['coefficients'], [1.75])
        self.assertIn('2*n', execution.dot(g))
        self.assertNotIn('1.75', execution.dot(g))

    def test_html_payload_escapes_script_boundary(self):
        f = Fixture(); f.call('</script><script>alert(1)</script>', {})
        g = execution.build(model(f))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'graph.html'; execution.write_html([g], p)
            page = p.read_text()
            self.assertEqual(page.count('</script>'), 1)
            self.assertIn('\\u003c/script\\u003e', page)


if __name__ == '__main__': unittest.main()
