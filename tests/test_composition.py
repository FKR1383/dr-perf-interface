"""Nesting, exact call relations, and preservation of unexplained child work."""
from pathlib import Path
from fractions import Fraction
import copy
import json
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import composition
import derive


class Fixture:
    def __init__(self):
        self.events = []
        self.seq = 0
        self.counts = {}

    def call(self, name, values, body=None, group="0:1", thread="1"):
        self.seq += 1
        event = {"region": name, "values": values, "group": group, "thread": thread,
                 "seq": self.seq}
        self.events.append(event)
        key = (name, tuple(values), tuple(values.values()))
        self.counts[key] = self.counts.get(key, 0) + 1
        if body:
            body()
        self.seq += 1
        event["end"] = self.seq

    def model(self, irregular=()):
        regions = {}
        for (name, names, state), count in self.counts.items():
            region = regions.setdefault(name, {"id": name, "states": list(names),
                "calls": 0, "points": [], "regimes": [{"coefficients": [5]*len(names),
                "constant": 7, "points": []}]})
            region["calls"] += count
            region["points"].append({"state": list(state), "calls": count, "recorded": 5*sum(state)+7})
            region["regimes"][0]["points"].append({"state": list(state),
                                                    "unexplained": 100*sum(state)**2 if name in irregular else 0})
        return list(regions.values())


def by_name(report):
    return {r["id"]: r for r in report["regions"]}


class Composition(unittest.TestCase):
    def test_two_parent_states_compose_child_call_multiplier(self):
        fixture = Fixture()
        for n in (0, 2):
            fixture.call("parent", {"n": n, "cold": 0},
                         lambda: [fixture.call("child", {"m": 7}) for _ in range(n)])
        report = composition.build(fixture.model(), fixture.events)
        edge = by_name(report)["parent"]["children"][0]
        self.assertEqual(composition.edge_text(edge, ["n", "cold"]), "(n)*F[child]")
        self.assertTrue(edge["includesZeroCallParents"])

    def test_single_child_with_opaque_pcvs_is_atomic_f(self):
        fixture = Fixture()
        for n in (1, 2, 4, 7):
            fixture.call('parent', {'n': n},
                         lambda: fixture.call('child', {'m': n*n}))
        report = composition.build(fixture.model(irregular=['child']), fixture.events)
        edge = by_name(report)['parent']['children'][0]
        self.assertIsNone(edge['arguments'])
        self.assertIsNone(edge['sequenceArguments'])
        self.assertEqual(edge['form'], 'product')
        self.assertEqual(composition.edge_text(edge, ['n']), 'F[child]')
        self.assertEqual(composition.edge_text(edge, ['n'], 'U'), 'U[child]')
        self.assertNotIn('sum[', '\n'.join(composition.lines(report)))

    def test_cross_function_product_keeps_irregular_child(self):
        fixture = Fixture()
        for n in (0, 1, 3, 8):
            for m in (2, 5, 11):
                fixture.call("parent", {"n": n, "m": m},
                             lambda: [fixture.call("library.child", {"size": m}) for _ in range(n)])
        report = composition.build(fixture.model(irregular=["library.child"]), fixture.events)
        self.assertEqual(report["status"], "observed")
        regions = by_name(report)
        edge = regions["parent"]["children"][0]
        self.assertEqual(edge["form"], "product")
        self.assertEqual(composition.edge_text(edge, ["n", "m"]), "(n)*F[library.child]")
        self.assertTrue(edge["includesZeroCallParents"])
        text = "\n".join(composition.lines(report))
        self.assertIn("U_own[library.child]", text)
        self.assertIn("(n)*U[library.child]", text)
        self.assertLess(text.index("F[library.child](size) ="), text.index("F[parent](n, m) ="))

    def test_varying_arguments_do_not_block_affine_child_multiplier(self):
        fixture = Fixture()
        for n in (1, 2, 4, 7):
            fixture.call("parent", {"n": n},
                         lambda: [fixture.call("child", {"m": i+1}) for i in range(n)])
        report = composition.build(fixture.model(), fixture.events)
        edge = by_name(report)["parent"]["children"][0]
        self.assertEqual(edge["form"], "product")
        self.assertIsNone(edge["arguments"])
        self.assertEqual(composition.edge_text(edge, ["n"]), "(n)*F[child]")

    def test_repeated_parent_state_with_different_call_counts_is_not_averaged(self):
        fixture = Fixture()
        for n, count in ((2, 2), (2, 7), (3, 3), (4, 4), (5, 5)):
            fixture.call("parent", {"n": n},
                         lambda: [fixture.call("child", {"m": 10}) for _ in range(count)])
        report = composition.build(fixture.model(), fixture.events)
        edge = by_name(report)["parent"]["children"][0]
        self.assertIsNone(edge["multiplicity"])
        self.assertEqual(composition.edge_text(edge, ["n"]), "unexplained(F[child])")
        row = next(r for r in by_name(report)["parent"]["observed"] if r["state"] == [2])
        self.assertEqual(row["childCallRanges"]["child"], [2, 7])

    def test_parent_j_pcv_does_not_collide_with_invocation_index(self):
        fixture = Fixture()
        for j in (1, 2, 4, 7):
            fixture.call("parent", {"j": j},
                         lambda: [fixture.call("child", {"m": 2*j+i}) for i in range(j)])
        report = composition.build(fixture.model(), fixture.events)
        edge = by_name(report)["parent"]["children"][0]
        self.assertEqual(composition.edge_text(edge, ["j"]),
                         "(j)*F[child]")

    def test_conditional_count_pcv_restores_product(self):
        fixture = Fixture()
        for n, selected in ((2, 0), (3, 1), (4, 0), (6, 3), (8, 2), (10, 5)):
            fixture.call("parent", {"n": n, "selected": selected},
                         lambda: [fixture.call("child", {"m": 10}) for _ in range(selected)])
        report = composition.build(fixture.model(), fixture.events)
        edge = by_name(report)["parent"]["children"][0]
        self.assertEqual(composition.edge_text(edge, ["n", "selected"]), "(selected)*F[child]")

    def test_three_levels_do_not_double_count_descendants(self):
        fixture = Fixture()
        for n in (1, 2, 3, 4):
            fixture.call("outer", {"n": n}, lambda: [
                fixture.call("middle", {"n": n}, lambda: [
                    fixture.call("leaf", {"n": n}) for _ in range(n)]) for _ in range(n)])
        report = composition.build(fixture.model(), fixture.events)
        regions = by_name(report)
        self.assertEqual([edge["child"] for edge in regions["outer"]["children"]], ["middle"])
        self.assertEqual([edge["child"] for edge in regions["middle"]["children"]], ["leaf"])
        self.assertEqual([r["id"] for r in report["regions"]], ["leaf", "middle", "outer"])

    def test_recursion_is_finite_recurrence(self):
        fixture = Fixture()
        def call(n):
            fixture.call("recursive", {"n": n}, lambda: call(n-1) if n else None)
        call(7)
        report = composition.build(fixture.model(), fixture.events)
        region = by_name(report)["recursive"]
        self.assertTrue(region["recursive"])
        self.assertEqual(region["children"][0]["form"], "unresolved")
        self.assertEqual(region["children"][0]["childCalls"], 7)

    def test_no_cross_thread_or_process_parentage(self):
        fixture = Fixture()
        fixture.call("outer", {"n": 1}, lambda: fixture.call("other", {"n": 2}, thread="2"))
        fixture.call("outer", {"n": 2}, lambda: fixture.call("other", {"n": 3}, group="1:2"))
        report = composition.build(fixture.model(), fixture.events)
        self.assertFalse(by_name(report)["outer"]["children"])

    def test_missing_trace_and_crossing_boundaries_are_rejected(self):
        fixture = Fixture()
        fixture.call("outer", {"n": 1}, lambda: fixture.call("child", {"n": 2}))
        self.assertEqual(composition.build(fixture.model(), fixture.events[:-1])["status"], "unavailable")
        fixture.events[-1]["end"] = fixture.events[0]["end"] + 1
        self.assertEqual(composition.build(fixture.model(), fixture.events)["status"], "unavailable")

    def test_dropped_and_invalid_measurements_cannot_compose(self):
        fixture = Fixture()
        fixture.call("outer", {"n": 1})
        model = fixture.model()
        model[0]["droppedCalls"] = 1
        self.assertEqual(composition.build(model, fixture.events)["status"], "unavailable")
        self.assertEqual(composition.build(fixture.model(), fixture.events, ["invalid"])["status"], "unavailable")

    def test_composition_does_not_add_marker_calibration_back(self):
        fixture = Fixture()
        fixture.call("parent", {"n": 1}, lambda: fixture.call("child", {"m": 2}))
        model = fixture.model()
        for region in model:
            region["markerCalibration"] = 100
            region["regimes"][0]["constant"] = 7
        report = composition.build(model, fixture.events)
        self.assertTrue(all(r["own"][0]["constant"] == 7 for r in report["regions"]))

    def test_insufficient_child_states_do_not_disappear(self):
        fixture = Fixture()
        fixture.call("parent", {"n": 1}, lambda: fixture.call("child", {"m": 2}))
        model = fixture.model()
        next(r for r in model if r["id"] == "child")["regimes"] = []
        report = composition.build(model, fixture.events)
        self.assertTrue(by_name(report)["child"]["ownUnexplained"])
        self.assertIn("F[child](m) = 0 + U_own[child](m)", "\n".join(composition.lines(report)))

    def test_portable_int64_unexplained_table_keeps_exact_states(self):
        import explorer
        fixture = Fixture()
        large = 2**60 + 3
        fixture.call("parent", {"n": 1}, lambda: fixture.call("child", {"m": large}))
        report = explorer.portable(composition.build(fixture.model(irregular=["child"]), fixture.events))
        text = "\n".join(composition.lines(report))
        self.assertIn(f"m={large:,}", text)


class ExactRelations(unittest.TestCase):
    def test_tiny_count_deviation_is_not_instruction_tolerance(self):
        values = [100, 200, 300, 401, 500]
        self.assertIsNone(composition.affine([(i,) for i in range(1, 6)], values, ["n"]))

    def test_int64_and_rational_coefficients(self):
        base = 2**60
        relation = composition.affine([(base+2*i,) for i in range(6)], list(range(6)), ["n"])
        self.assertEqual(relation["coefficients"], ["1/2"])
        self.assertEqual(relation["constant"], str(-base//2))

    def test_two_states_support_observed_affine_relation(self):
        relation = composition.affine([(1,), (2,)], [3, 5], ["n"])
        self.assertEqual(composition.affine_text(relation, ["n"]), "2*n + 1")
        self.assertEqual(relation["samples"], 2)
        self.assertEqual(relation["kind"], "observed-affine")

    def test_sparse_dependent_pcvs_fit_without_extra_observation(self):
        relation = composition.affine([(1, 2, 0), (2, 4, 0)], [3, 5], ["n", "m", "cold"])
        self.assertEqual(composition.affine_text(relation, ["n", "m", "cold"]), "2*n + 1")
        self.assertEqual(relation["dependent"], ["m", "cold"])

    def test_sparse_fit_still_rejects_conflicting_observations(self):
        self.assertIsNone(composition.affine([(1,), (2,), (2,)], [3, 5, 6], ["n"]))
        self.assertIsNone(composition.affine([(1,), (2,), (3,)], [3, 5, 8], ["n"]))

    def test_single_state_constant_and_empty_input(self):
        relation = composition.affine([(10, 0)], [3], ["n", "cold"])
        self.assertEqual(composition.affine_text(relation, ["n", "cold"]), "3")
        self.assertEqual(relation["kind"], "observed-constant")
        self.assertIsNone(composition.affine([], [], ["n"]))

    def test_dependent_parent_pcvs_disclosed(self):
        relation = composition.affine([(i, 2*i) for i in range(5)], list(range(5)), ["n", "m"])
        self.assertEqual(relation["dependent"], ["m"])

    def test_dimension_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            composition.affine([(1,), (2,)], [1], ["n"])

    def test_random_exact_planes_permutations_and_contradictions(self):
        rng = random.Random(9147)
        for case in range(100):
            width = 1 + case % 8
            names = [f"x{i}" for i in range(width)]
            coefficients = [Fraction(rng.randrange(-9, 10), 3) for _ in names]
            offset = rng.randrange(-100, 100)
            rows = [tuple(rng.randrange(-50, 51) for _ in names) for _ in range(width+8)]
            values = [offset + sum(a*x for a, x in zip(coefficients, row)) for row in rows]
            pairs = list(zip(rows, values))
            rng.shuffle(pairs)
            relation = composition.affine([p[0] for p in pairs], [p[1] for p in pairs], names)
            self.assertIsNotNone(relation, case)
            for _ in range(4):
                row = tuple(rng.randrange(-100, 100) for _ in names)
                actual = Fraction(relation['constant']) + sum(Fraction(a)*x for a, x in zip(relation['coefficients'], row))
                self.assertEqual(actual, offset + sum(a*x for a, x in zip(coefficients, row)))
            self.assertIsNone(composition.affine(rows + [rows[0]], values + [values[0]+1], names))

    def test_sixty_four_parent_pcvs(self):
        width = 64
        names = [f'x{i}' for i in range(width)]
        rows = [tuple([0]*width)] + [tuple(int(i == j) for i in range(width)) for j in range(width)]
        rows.append(tuple([1]*width))
        values = [17 + sum((i+1)*x for i, x in enumerate(row)) for row in rows]
        relation = composition.affine(rows, values, names)
        self.assertEqual(relation['coefficients'], [str(i+1) for i in range(width)])
        self.assertEqual(relation['constant'], '17')

    def test_random_dependent_planes_keep_predictions_after_reordering(self):
        rng = random.Random(243)
        names = ['x', 'y', 'x_plus_y', 'twice_x']
        for _ in range(20):
            rows = [(x, y, x+y, 2*x) for x, y in ((rng.randrange(20), rng.randrange(20)) for _ in range(12))]
            values = [7*x-3*y+5 for x, y, _, _ in rows]
            first = composition.affine(rows, values, names)
            self.assertTrue(first['dependent'])
            for row, value in zip(rows, values):
                self.assertEqual(Fraction(first['constant']) + sum(Fraction(a)*x for a, x in zip(first['coefficients'], row)), value)


class StructuralChecks(unittest.TestCase):
    def test_argument_order_survives_sorted_json(self):
        fixture = Fixture()
        for n in (1, 2, 4, 7):
            for m in (3, 6, 9):
                fixture.call('parent', {'n': n, 'm': m}, lambda: fixture.call('child', {'z': n, 'a': m}))
        report = composition.build(fixture.model(), fixture.events)
        reordered = json.loads(json.dumps(report, sort_keys=True))
        edge = by_name(reordered)['parent']['children'][0]
        self.assertEqual(composition.edge_text(edge, ['n', 'm']), 'F[child]')

    def test_mutually_recursive_components_all_marked(self):
        fixture = Fixture()
        def call(n):
            fixture.call('even' if n % 2 == 0 else 'odd', {'n': n}, lambda: call(n-1) if n else None)
        call(8)
        report = composition.build(fixture.model(), fixture.events)
        self.assertTrue(all(r['recursive'] for r in report['regions']))

    def test_deep_nesting_does_not_use_python_recursion(self):
        depth = 1200
        model, events = [], []
        for i in range(depth):
            fixture = Fixture()
            fixture.call(str(i), {'n': i})
            model.extend(fixture.model())
            event = fixture.events[0]
            event.update(seq=i+1, end=2*depth-i)
            events.append(event)
        report = composition.build(model, events)
        self.assertEqual(report['status'], 'observed')
        self.assertEqual(len(report['regions']), depth)
        self.assertEqual(sum(len(r['children']) for r in report['regions']), depth-1)
        self.assertFalse(any(r['recursive'] for r in report['regions']))

    def test_random_forest_edges_against_interval_oracle(self):
        rng = random.Random(127)
        for run in range(20):
            fixture = Fixture()
            def node(depth):
                name, value = f'r{rng.randrange(6)}', rng.randrange(8)
                def children():
                    if depth < 4:
                        for _ in range(rng.randrange(3)):
                            node(depth+1)
                fixture.call(name, {'n': value}, children)
            for _ in range(5):
                node(0)
            expected = {}
            for event in fixture.events:
                parents = [p for p in fixture.events if p['seq'] < event['seq'] and p['end'] > event['end']]
                if parents:
                    parent = max(parents, key=lambda p: p['seq'])
                    key = parent['region'], event['region']
                    expected[key] = expected.get(key, 0) + 1
            report = composition.build(fixture.model(), list(reversed(fixture.events)))
            actual = {(r['id'], e['child']): e['childCalls'] for r in report['regions'] for e in r['children']}
            self.assertEqual(actual, expected, run)
            for region in report['regions']:
                root = region['id']
                pending = [child for parent, child in expected if parent == root]
                reached = set()
                while pending:
                    child = pending.pop()
                    if child not in reached:
                        reached.add(child)
                        pending.extend(c for p, c in expected if p == child)
                self.assertEqual(region['recursive'], root in reached, (run, root))

    def test_fractional_boolean_and_nonfinite_states_are_rejected(self):
        for value in (1.25, True, float('nan'), float('inf'), '1.5'):
            fixture = Fixture()
            fixture.call('r', {'n': 1})
            model = fixture.model()
            fixture.events[0]['values']['n'] = value
            self.assertEqual(composition.build(model, fixture.events)['status'], 'unavailable')

    def test_duplicate_interfaces_and_wrong_call_totals_are_rejected(self):
        fixture = Fixture()
        fixture.call('r', {'n': 1})
        model = fixture.model()
        self.assertEqual(composition.build(model + model, fixture.events)['status'], 'unavailable')
        model[0]['calls'] = 20
        self.assertEqual(composition.build(model, fixture.events)['status'], 'unavailable')

    def test_zero_pcv_child_remains_an_opaque_interface(self):
        fixture = Fixture()
        for n in range(5):
            fixture.call('parent', {'n': n}, lambda: [fixture.call('child', {}) for _ in range(n)])
        report = composition.build(fixture.model(), fixture.events)
        edge = by_name(report)['parent']['children'][0]
        self.assertEqual(composition.edge_text(edge, ['n']), '(n)*F[child]')

    def test_decimal_string_boundaries_are_ordered_numerically(self):
        fixture = Fixture()
        for n in range(6):
            fixture.call('parent', {'n': n}, lambda: fixture.call('child', {'n': n}))
        model = fixture.model()
        for event in fixture.events:
            event['seq'], event['end'] = str(event['seq']), str(event['end'])
        for region in model:
            region['calls'] = str(region['calls'])
            for point in region['points']:
                point['calls'] = str(point['calls'])
        self.assertEqual(composition.build(model, fixture.events)['status'], 'observed')


class FrozenChecks(unittest.TestCase):
    def program(self, ns=(1, 2, 4, 7), extra=0, argument_shift=0, new_child=False, reorder=False):
        fixture = Fixture()
        for n in ns:
            for m in (3, 8):
                def children():
                    for _ in range(n+extra):
                        values = {'m': m+argument_shift, 'twice': 2*m}
                        if reorder:
                            values = dict(reversed(list(values.items())))
                        fixture.call('child', values)
                    if new_child:
                        fixture.call('new_child', {'n': n})
                values = {'n': n, 'm': m}
                if reorder:
                    values = dict(reversed(list(values.items())))
                fixture.call('parent', values, children)
        return fixture

    def setUp(self):
        self.base = self.program()
        self.reference = composition.build(self.base.model(), self.base.events)

    def check_fixture(self, fixture):
        return composition.check(self.reference, fixture.model(), fixture.events)

    def test_new_inputs_check_without_refitting(self):
        original = copy.deepcopy(self.reference)
        result = self.check_fixture(self.program(ns=(3, 5, 8, 10)))
        self.assertEqual(result['edges'][0]['status'], 'holds')
        self.assertGreater(result['edges'][0]['checks'], 8)
        self.assertEqual(self.reference, original)

    def test_one_extra_call_at_every_parent_is_detected(self):
        result = self.check_fixture(self.program(ns=(3, 5, 8, 10), extra=1))
        row = result['edges'][0]
        self.assertEqual(row['status'], 'fails')
        self.assertEqual(row['failures'], 8)
        self.assertEqual(row['counterexamples'][0]['kind'], 'multiplicity')

    def test_changed_arguments_are_detected(self):
        fixture = self.program(argument_shift=1)
        result = self.check_fixture(fixture)
        row = result['edges'][0]
        self.assertEqual(row['failures'], 2*sum((1, 2, 4, 7)))
        self.assertEqual(row['counterexamples'][0]['kind'], 'argument:m')

    def test_pcv_reordering_does_not_change_meaning(self):
        result = self.check_fixture(self.program(reorder=True))
        self.assertEqual(result['edges'][0]['status'], 'holds')

    def test_new_child_edge_is_reported(self):
        result = self.check_fixture(self.program(new_child=True))
        self.assertEqual(result['newEdges'], [{'parent': 'parent', 'child': 'new_child'}])

    def test_missing_child_is_zero_calls_not_not_exercised(self):
        fixture = Fixture()
        for n in range(1, 5):
            fixture.call('parent', {'n': n, 'm': 3})
        result = self.check_fixture(fixture)
        self.assertEqual(result['edges'][0]['failures'], 4)

    def test_missing_parent_is_not_exercised(self):
        fixture = Fixture()
        fixture.call('child', {'m': 3, 'twice': 6})
        self.assertEqual(self.check_fixture(fixture)['edges'][0]['status'], 'not-exercised')

    def test_changed_schema_is_not_silently_rebound(self):
        fixture = Fixture()
        fixture.call('parent', {'n': 1, 'different': 3}, lambda: fixture.call('child', {'m': 3, 'twice': 6}))
        self.assertEqual(self.check_fixture(fixture)['edges'][0]['status'], 'schema-mismatch')

    def test_known_count_with_opaque_arguments_accepts_multiplier(self):
        fixture = Fixture()
        for n in range(2, 6):
            fixture.call('parent', {'n': n}, lambda: [fixture.call('child', {'m': i*i+1}) for i in range(n)])
        reference = composition.build(fixture.model(), fixture.events)
        result = composition.check(reference, fixture.model(), fixture.events)
        row = result['edges'][0]
        self.assertEqual(row['status'], 'holds')
        self.assertFalse(row['unresolved'])
        self.assertTrue(row['argumentsUnresolved'])

    def test_invalid_measured_trace_cannot_validate(self):
        result = composition.check(self.reference, self.base.model(), self.base.events[:-1])
        self.assertEqual(result['status'], 'unavailable')


if __name__ == "__main__":
    unittest.main()
