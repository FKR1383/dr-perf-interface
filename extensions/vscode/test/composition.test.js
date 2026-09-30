'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const Model = require('../media/model');
const demo = require('../demo/pipeline.drperf.json');
const affine = (coefficients, constant = '0') => ({ coefficients, constant });
function fixture() {
  const model = structuredClone(demo);
  model.composition = { status: 'observed', regions: [{
    id: 'enqueue', states: ['items'], children: [{
      child: 'copy', form: 'product', indexVariable: 'j', argumentStates: ['bytes'],
      multiplicity: affine(['2'], '1'), arguments: { bytes: affine(['8']) },
      sequenceArguments: null
    }]
  }] };
  return model;
}

test('child interfaces remain references, with own numeric formulas unchanged', () => {
  const model = fixture();
  const before = JSON.stringify(model);
  Model.validate(model);
  assert.deepEqual(Model.childTerms(model, 'enqueue'), [{
    child: 'copy', prefix: '(2*items + 1)*', reference: 'F[copy]', suffix: ''
  }]);
  assert.deepEqual(Model.childTerms(model, 'copy'), []);
  assert.equal(JSON.stringify(model), before);
  assert.ok(!Model.formula(model.regions.find((r) => r.id === 'enqueue')).includes('copy'));
});

test('irregular child counts stay unexplained, while arguments remain separate', () => {
  const model = fixture(), edge = model.composition.regions[0].children[0];
  edge.form = 'sum';
  edge.multiplicity = null;
  edge.arguments = null;
  edge.sequenceArguments = { bytes: affine(['1/2', '1']) };
  Model.validate(model);
  assert.deepEqual(Model.childTerms(model, 'enqueue'), [{
    child: 'copy', prefix: 'unexplained(', reference: 'F[copy]', suffix: ')'
  }]);
  edge.sequenceArguments = null;
  assert.equal(Model.childTerms(model, 'enqueue')[0].reference, 'F[copy]');
});

test('recursive interfaces do not recursively expand, and unavailable composition stays absent', () => {
  const model = fixture(), edge = model.composition.regions[0].children[0];
  edge.child = 'enqueue';
  edge.argumentStates = ['items'];
  edge.arguments = { items: affine(['1'], '-1') };
  Model.validate(model);
  assert.equal(Model.childTerms(model, 'enqueue')[0].reference, 'F[enqueue]');
  model.composition.status = 'unavailable';
  assert.deepEqual(Model.childTerms(model, 'enqueue'), []);
});

test('old sum-form reports with one child render as F without needing argument fits', () => {
  const model = fixture(), edge = model.composition.regions[0].children[0];
  edge.form = 'sum';
  edge.multiplicity = affine(['0'], '1');
  edge.arguments = null;
  edge.sequenceArguments = null;
  Model.validate(model);
  assert.deepEqual(Model.childTerms(model, 'enqueue'), [{
    child: 'copy', prefix: '', reference: 'F[copy]', suffix: ''
  }]);
  edge.form = 'product';
  edge.multiplicity = affine(['2'], '3');
  Model.validate(model);
  assert.equal(Model.childTerms(model, 'enqueue')[0].prefix, '(2*items + 3)*');
});

test('rejects malformed composition before rendering clickable terms', () => {
  for (const change of [
    (edge) => { edge.child = 'missing'; },
    (edge) => { edge.arguments = {}; },
    (edge) => { edge.multiplicity.coefficients = ['1', '2']; },
    (edge) => { edge.multiplicity.constant = '1/0'; },
    (edge) => { edge.argumentStates = ['wrong']; }
  ]) {
    const model = fixture();
    change(model.composition.regions[0].children[0]);
    assert.throws(() => Model.validate(model));
  }
});

test('integer formatting changes presentation only', () => {
  const region = { states: ['n'], regimes: [{ coefficients: [12.6], constant: -3.2,
    blocks: {unexplained: 0}, dependent: [], range: [[1, 20]],
    points: [{state: [10], unexplained: 0}] }] };
  assert.equal(Model.formula(region), '13*n - 3');
  assert.equal(Model.format(1234.7), '1,235');
  assert.equal(Model.format(-0.2), '0');
  assert.equal(region.regimes[0].coefficients[0], 12.6);
  assert.equal(Model.evaluate(region, {n: 10}).explained, 122.8);
});

// Two children: one resolved, one unresolved. Each has a costly grandchild.
// Fully unexplained work below a resolved edge must stay atomic at its parent.
function costFixture() {
  const model = structuredClone(demo);
  model.relations = [];
  const region = (name, observations) => ({
    id: name, name, states: ['n'], sources: [], droppedCalls: 0,
    calls: observations.reduce((n, p) => n + p[3], 0),
    points: observations.map(([n, cost, u, calls]) => ({state: [n], observed: cost, recorded: cost, calls})),
    regimes: [{coefficients: [0], constant: 100, dependent: [], range: [[0, 9]],
      unexplainedShare: observations.reduce((s, p) => s + p[2], 0) / observations.reduce((s, p) => s + p[1], 0),
      points: observations.map(([n, cost, u, calls]) => ({state: [n], explained: cost-u, unexplained: u, calls})),
      blocks: {unexplained: 1}, attribution: {coefficients: [[]], constant: [], unexplained: []}}]
  });
  model.regions = [region('parent', [[0, 100, 10, 1]]), region('good', [[0, 200, 180, 1]]),
    region('bad', [[0, 100, 0, 1]]), region('leaf', [[1, 300, 300, 1], [2, 400, 400, 1]])];
  const event = (region, n, seq, end) => ({region, values: {n}, seq, end, group: '0:1', thread: '1'});
  model.trace = {complete: true, recordCount: 5, events: [event('parent', 0, 1, 10),
    event('good', 0, 2, 5), event('leaf', 1, 3, 4),
    event('bad', 0, 6, 9), event('leaf', 2, 7, 8)]};
  const edge = (child, resolved = true) => ({child, form: resolved ? 'product' : 'unresolved',
    indexVariable: 'j', argumentStates: ['n'], arguments: null, sequenceArguments: null,
    multiplicity: resolved ? affine(['0'], '1') : null});
  model.composition = {status: 'observed', regions: [
    {id: 'parent', states: ['n'], children: [edge('good'), edge('bad', false)]},
    {id: 'good', states: ['n'], children: [edge('leaf')]},
    {id: 'bad', states: ['n'], children: [edge('leaf')]},
    {id: 'leaf', states: ['n'], children: []}]};
  Model.validate(model);
  return model;
}

test('parent unexplained includes the full unresolved child subtree but not resolved child residuals', () => {
  const model = costFixture(), before = JSON.stringify(model);
  const result = Model.interfaceExplanation(model, 'parent');
  assert.equal(result.total, 1100); // own 100 + good subtree 500 + bad subtree 500
  assert.equal(result.ownUnexplained, 10);
  assert.equal(result.unresolvedChildCost, 500);
  assert.equal(result.share, 510 / 1100);
  assert.equal(result.estimated, true);
  assert.deepEqual(result.children, [{child: 'bad', share: 500 / 1100}]);
  assert.equal(Model.interfaceExplanation(model, 'good').share, 180 / 500);
  assert.equal(Model.interfaceExplanation(model, 'bad').share, 0);
  assert.equal(Model.interfaceExplanation(model, 'leaf').share, 1);
  assert.equal(JSON.stringify(model), before);
});

test('fitting a child multiplier removes its whole contribution from parent unexplained', () => {
  const model = costFixture();
  const edge = model.composition.regions[0].children[1];
  edge.multiplicity = affine(['0'], '1'); edge.form = 'product';
  const result = Model.interfaceExplanation(model, 'parent');
  assert.equal(result.unresolvedChildCost, 0);
  assert.equal(result.share, 10 / 1100);
  assert.deepEqual(result.children, []);
});

test('child contribution uses actual zero-call parents and averages within each state', () => {
  const model = costFixture(), parent = model.regions[0];
  parent.calls = parent.points[0].calls = parent.regimes[0].points[0].calls = 2;
  model.trace.events.push({region: 'parent', values: {n: 0}, seq: 11, end: 12, group: '0:1', thread: '1'});
  model.trace.recordCount++;
  const result = Model.interfaceExplanation(model, 'parent');
  assert.equal(result.total, 600); // own 100 + child subtrees 1000 / 2
  assert.equal(result.unresolvedChildCost, 250);
  assert.equal(result.share, 260 / 600);
});

test('regime percentages include only child calls at that regime’s parent states', () => {
  const model = costFixture(), parent = model.regions[0];
  const second = structuredClone(parent.regimes[0]);
  second.points = [{state: [1], explained: 100, unexplained: 0, calls: 2}];
  second.unexplainedShare = 0;
  parent.regimes.push(second);
  parent.points.push({state: [1], observed: 100, calls: 2}); parent.calls += 2;
  model.trace.events.push(
    {region: 'parent', values: {n: 1}, seq: 11, end: 12, group: '0:1', thread: '1'},
    {region: 'parent', values: {n: 1}, seq: 13, end: 14, group: '0:1', thread: '1'});
  model.trace.recordCount += 2;
  assert.equal(Model.interfaceExplanation(model, 'parent', parent.regimes[0]).share, 510 / 1100);
  assert.equal(Model.interfaceExplanation(model, 'parent', second).share, 0);
  assert.equal(Model.interfaceExplanation(model, 'parent').share, 510 / 1200); // distinct states, not call-weighted
});

test('missing and invalid child evidence cannot silently report zero unexplained', () => {
  for (const mutate of [
    (m) => { m.trace.complete = false; },
    (m) => { m.trace.events.pop(); },
    (m) => { m.validity.errors = ['overflow']; },
    (m) => { m.regions[2].points[0].observed = -1; },
    (m) => { m.composition.regions[2].children = []; }
  ]) {
    const model = costFixture(); mutate(model);
    const result = Model.interfaceExplanation(model, 'parent');
    assert.equal(result.share, null);
    assert.ok(result.reason);
  }
});

test('recursive child work is accounted by finite call nesting, without infinite expansion', () => {
  const model = costFixture();
  model.regions = [model.regions[3]];
  const r = model.regions[0];
  r.points = [{state: [1], observed: 100, calls: 1}, {state: [2], observed: 200, calls: 1}];
  r.regimes[0].points = r.points.map((p) => ({...p, explained: p.observed, unexplained: 0}));
  r.regimes[0].unexplainedShare = 0;
  model.composition.regions = [{id: 'leaf', states: ['n'], children: [
    {...model.composition.regions[0].children[1], child: 'leaf'}]}];
  model.trace.events = [
    {region: 'leaf', values: {n: 1}, seq: 1, end: 4, group: '0:1', thread: '1'},
    {region: 'leaf', values: {n: 2}, seq: 2, end: 3, group: '0:1', thread: '1'}];
  model.trace.recordCount = 2;
  const result = Model.interfaceExplanation(model, 'leaf');
  assert.equal(result.total, 500); // outer subtree 300 + inner subtree 200, one point each
  assert.equal(result.unresolvedChildCost, 200);
  assert.equal(result.share, 0.4);
});

test('unfitted own work remains unexplained while resolved children remain atomic', () => {
  const model = costFixture(); model.regions[0].regimes = [];
  assert.equal(Model.interfaceExplanation(model, 'parent').share, 600 / 1100);
});
