'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Model = require('../media/model');
const reportPath = path.resolve(__dirname, '../demo/pipeline.drperf.json');
const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
const clone = () => structuredClone(report);
function assumptions(model = report) {
  const chosen = new Map();
  for (const r of model.relations) {
    const key = Model.id(r.target.region, r.target.state);
    if (!chosen.has(key)) chosen.set(key, r.id);
  }
  return [...chosen.values()];
}

test('zero intervention replays original states under observed equations', () => {
  const result = Model.replay(report, {
    edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 1 }],
    relations: assumptions()
  });
  assert.equal(
    result.regions.reduce((n, r) => n + r.changedCalls, 0),
    0
  );
  for (const row of result.regions) if (row.modelledCalls) assert.equal(row.delta, 0);
});

test('one producer PCV change propagates through queue and several regions', () => {
  const result = Model.replay(report, {
    edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
    relations: assumptions()
  });
  for (const name of ['enqueue', 'dequeue', 'decode', 'copy']) {
    const row = result.regions.find((r) => r.region === name);
    assert.ok(row.changedCalls > 0, name);
    assert.ok(row.delta > 0, name);
  }
  assert.equal(result.regions.find((r) => r.region === 'startup').changedCalls, 0);
  assert.ok(!Object.hasOwn(result, 'totalCost'));
  assert.ok(result.regions.find((r) => r.region === 'lookup').unexplainedCalls > 0);
});

test('relationships do not silently become causal propagation', () => {
  const result = Model.replay(report, {
    edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
    relations: []
  });
  assert.equal(result.regions.find((r) => r.region === 'copy').changedCalls, 0);
});

test('alternatives for the same target cannot be applied simultaneously', () => {
  const ids = report.relations.filter((r) => r.target.region === 'copy').map((r) => r.id);
  assert.throws(
    () =>
      Model.replay(report, {
        edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
        relations: ids
      }),
    /Choose one/
  );
});

test('invalid and incomplete measurements disable predictions', () => {
  const m = clone();
  m.trace.complete = false;
  assert.throws(() => Model.replay(m, {}), /complete recorded trace/);
  m.trace.complete = true;
  m.validity.errors = ['overflow'];
  assert.throws(() => Model.replay(m, {}), /validity/);
});

test('report metadata cannot relabel time or a textual false flag as complete instruction measurements', () => {
  const time = clone();
  time.measurement.unit = 'seconds';
  assert.throws(() => Model.validate(time), /measurement scope/);
  const incomplete = clone();
  incomplete.trace.complete = 'false';
  assert.throws(() => Model.validate(incomplete), /completeness/);
  const missing = clone();
  delete missing.validity;
  assert.throws(() => Model.validate(missing), /validity/);
});

test('int64 state values remain viewable but never rounded for replay', () => {
  const m = clone();
  m.trace.events[0].values = { once: '9007199254740993' };
  assert.doesNotThrow(() => Model.validate(m));
  assert.throws(
    () =>
      Model.replay(m, { edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }] }),
    /exact integer range/
  );
});

test('unobserved correlated states are not identifiable', () => {
  const region = {
    states: ['n', 'm'],
    regimes: [
      {
        coefficients: [5, 0],
        constant: 1,
        dependent: ['m'],
        range: [
          [1, 3],
          [2, 6]
        ],
        points: [{ state: [1, 2], unexplained: 0 }],
        blocks: { unexplained: 0 }
      }
    ]
  };
  assert.ok(Model.evaluate(region, { n: 1, m: 2 }).ok);
  assert.match(Model.evaluate(region, { n: 2, m: 3 }).reason, /not identifiable/);
});

test('regime gaps remain unknown and extrapolation is labelled', () => {
  const region = {
    states: ['n'],
    regimes: [
      {
        coefficients: [2],
        constant: 0,
        dependent: [],
        range: [[1, 3]],
        points: [{ state: [1], unexplained: 0 }],
        blocks: { unexplained: 0 }
      },
      {
        coefficients: [4],
        constant: 0,
        dependent: [],
        range: [[7, 9]],
        points: [{ state: [9], unexplained: 0 }],
        blocks: { unexplained: 0 }
      }
    ]
  };
  assert.match(Model.evaluate(region, { n: 5 }).reason, /branch boundary/);
  assert.equal(Model.evaluate(region, { n: 10 }).support, 'extrapolated');
  assert.equal(Model.evaluate(region, { n: 2 }).support, 'unobserved');
});

test('negative formula intercept is retained', () => {
  const r = {
    states: ['depth'],
    regimes: [
      {
        coefficients: [100],
        constant: -100,
        dependent: [],
        range: [[1, 8]],
        points: [{ state: [1], unexplained: 0 }],
        blocks: { unexplained: 0 }
      }
    ]
  };
  assert.equal(Model.evaluate(r, { depth: 1 }).explained, 0);
  assert.equal(Model.evaluate(r, { depth: 3 }).explained, 200);
  assert.match(Model.formula(r), /- 100/);
});

test('overlapping regime ranges cannot choose an unobserved branch by array order', () => {
  const region = {
    states: ['n'],
    regimes: [
      {
        coefficients: [2],
        constant: 0,
        dependent: [],
        range: [[1, 5]],
        points: [{ state: [1], unexplained: 0 }],
        blocks: { unexplained: 0 }
      },
      {
        coefficients: [4],
        constant: 0,
        dependent: [],
        range: [[3, 7]],
        points: [{ state: [7], unexplained: 0 }],
        blocks: { unexplained: 0 }
      }
    ]
  };
  assert.match(Model.evaluate(region, { n: 4 }).reason, /ambiguous/);
  region.regimes.reverse();
  assert.match(Model.evaluate(region, { n: 4 }).reason, /ambiguous/);
  assert.equal(Model.evaluate(region, { n: 1 }).explained, 2);
});

test('relationship evaluation uses exact fractions, including cancellation', () => {
  const relation = {
    target: { region: 'target', state: 'n' },
    constant: 0,
    constantExact: '0',
    terms: [
      { coefficient: 1 / 3, coefficientExact: '1/3', kind: 'last', region: 'source', state: 'n' },
      { coefficient: 2 / 3, coefficientExact: '2/3', kind: 'last', region: 'source', state: 'n' }
    ]
  };
  assert.equal(
    Model.exactRelationshipValue(relation, () => 9007199254740989),
    9007199254740989
  );
  relation.terms.pop();
  assert.throws(() => Model.exactRelationshipValue(relation, () => 10), /non-integer/);
  assert.equal(
    Model.exactRelationshipValue(relation, () => 9),
    3
  );
  assert.match(Model.relationship(relation), /1\/3/);
});

test('all exported relationships independently verify against the trace', () => {
  const checks = Model.verifyRelationships(report);
  assert.equal(checks.length, report.relations.length);
  assert.ok(checks.every((c) => c.holds && c.calls >= 5));
});

test('a tampered observed equation gives counterexamples and cannot silently propagate', () => {
  const m = clone(),
    r = m.relations.find((r) => r.target.region === 'copy');
  r.constant = 1;
  r.constantExact = '1';
  const check = Model.verifyRelationships(m, [r.id])[0];
  assert.equal(check.holds, false);
  assert.ok(check.mismatches > 0);
  assert.ok(check.examples.length);
  assert.throws(
    () =>
      Model.replay(m, {
        edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
        relations: [r.id]
      }),
    /does not hold/
  );
});

test('scenario validation rejects a changed call structure instead of inventing alignment', () => {
  const changed = clone();
  const removed = changed.trace.events.pop();
  --changed.trace.recordCount;
  --changed.regions.find((r) => r.id === removed.region).calls;
  const result = Model.validateScenario(
    report,
    { edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 1 }], relations: [] },
    changed
  );
  assert.equal(result.structureMatches, false);
  assert.equal(result.regions.length, 0);
});

test('incomplete or mismatched trace metadata cannot silently support scenarios', () => {
  const input = {
    edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
    relations: []
  };
  const missing = clone();
  missing.trace.events.pop();
  assert.throws(() => Model.replay(missing, input), /completeness metadata/);
  --missing.trace.recordCount;
  assert.throws(() => Model.replay(missing, input), /differ from measured calls/);
  const renamed = clone();
  renamed.trace.events.find((e) => e.region === 'enqueue').values = { other: 7 };
  assert.throws(() => Model.replay(renamed, input), /PCV fields/);
  assert.throws(
    () =>
      Model.proposeRelationship(
        renamed,
        { region: 'copy', state: 'bytes' },
        '8 * last("decode", "tokens")'
      ),
    /PCV fields/
  );
  assert.doesNotThrow(() => Model.validate(missing), 'recorded interfaces remain viewable');
});

test('scenario validation separates state errors from formula errors', () => {
  const result = Model.validateScenario(
    report,
    { edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }], relations: [] },
    report
  );
  assert.ok(result.structureMatches);
  const enqueue = result.regions.find((r) => r.region === 'enqueue');
  assert.equal(enqueue.stateMatches, 0);
  assert.equal(enqueue.costChecks, 0);
});

test('integer display preserves terms without changing small fitted coefficients', () => {
  assert.equal(
    Model.formula(
      { states: ['bytes'] },
      { coefficients: [0.00003125], constant: 2, blocks: { unexplained: 0 } }
    ),
    '0*bytes + 2'
  );
});
test('malformed observations and source locations are rejected before rendering', () => {
  const bad = clone();
  bad.regions[0].sources[0].line = -1;
  assert.throws(() => Model.validate(bad), /source location/);
  const missing = clone();
  missing.regions[0].regimes[0].points[0].state = ['not an integer'];
  assert.throws(() => Model.validate(missing), /formula/);
});
test('validation refuses incompatible counting configurations', () => {
  const other = clone();
  other.provenance.runs[0].measurement.follow_unmarked_threads =
    !other.provenance.runs[0].measurement.follow_unmarked_threads;
  assert.throws(
    () =>
      Model.validateScenario(
        report,
        { edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 1 }] },
        other
      ),
    /settings differ/
  );
});

test('legacy recorded-count view undoes constant calibration without changing PCV slopes', () => {
  const model = clone(),
    region = model.regions.find((r) => r.id === 'enqueue');
  region.markerCalibration = 5000;
  for (const fit of region.regimes) {
    fit.markerCalibration = 5000;
    fit.constant -= 5000;
    for (const p of fit.points) p.explained -= 5000;
  }
  for (const point of region.points) point.observed -= 5000;
  const raw = Model.recordedCosts(model),
    original = report.regions.find((r) => r.id === 'enqueue'),
    restored = raw.regions.find((r) => r.id === 'enqueue');
  assert.deepEqual(restored.regimes[0].coefficients, original.regimes[0].coefficients);
  assert.ok(Math.abs(restored.regimes[0].constant - original.regimes[0].constant) < 1e-9);
  assert.equal(restored.points[0].observed, original.points[0].observed);
  assert.match(raw.measurement.markerAdjustment, /retained/);
  const scenario = {
    edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 1 }],
    costBasis: 'recorded'
  };
  const compared = Model.validateScenario(model, scenario, model);
  assert.equal(compared.regions.find((r) => r.region === 'enqueue').stateMatches, 48);
});

test('recorded-count view restores raw fits after state-dependent marker removal', () => {
  const model = clone();
  model.composition = { status: 'observed', regions: [{ id: 'enqueue' }], errors: [] };
  const region = model.regions.find((r) => r.id === 'enqueue');
  region.recordedRegimes = structuredClone(region.regimes);
  const saved = structuredClone(region.recordedRegimes);
  region.regimes[0].coefficients[0] -= 17;
  region.regimes[0].constant -= 9;
  region.regimes[0].points[0].unexplained = 123;
  region.diagnostics = ['Marker wrapper calibration mismatch', 'source changed'];
  for (const point of region.points) {
    point.recorded = point.observed;
    point.observed -= 17*point.state[0] + 9;
  }
  const raw = Model.recordedCosts(model);
  const restored = raw.regions.find((r) => r.id === 'enqueue');
  assert.deepEqual(restored.regimes, saved);
  assert.deepEqual(restored.diagnostics, ['source changed']);
  assert.ok(restored.points.every((point) => point.observed === point.recorded));
  assert.equal(Model.recordedCosts(raw), raw);
  assert.equal(raw.composition.status, 'unavailable', 'do not expose stale adjusted composition in a raw view');
  assert.notDeepEqual(region.regimes, saved, 'original adjusted model is unchanged');
});

test('changed calls retain the actual history values used by selected equations', () => {
  const result = Model.replay(report, {
    edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }],
    relations: assumptions()
  });
  const copy = result.regions.find((r) => r.region === 'copy').changes[0];
  const derivation = copy.derivations.find((d) => d.relationship);
  assert.ok(derivation.inputs.length);
  assert.equal(derivation.result, copy.after.bytes);
  assert.match(derivation.equation, /copy.bytes/);
  const direct = result.regions
    .find((r) => r.region === 'enqueue')
    .changes[0].derivations.find((d) => d.intervention);
  assert.equal(direct.result, 2 * direct.before);
});

test('duplicate end markers and crossing thread boundaries cannot masquerade as complete traces', () => {
  const duplicate = clone();
  duplicate.trace.events[1].end = duplicate.trace.events[0].end;
  duplicate.trace.events[1].seq = 0;
  assert.throws(() => Model.validate(duplicate), /Duplicate|Crossing/);
  const crossed = clone();
  const events = crossed.trace.events.slice(0, 2);
  events[0].seq = 1;
  events[0].end = 4;
  events[1].seq = 2;
  events[1].end = 5;
  events[1].thread = events[0].thread;
  crossed.trace.events = events;
  assert.throws(() => Model.validate(crossed), /Crossing/);
});

test('an intervention distinguishes observationally equivalent relationship alternatives', () => {
  const input = {
    edits: [{ region: 'decode', state: 'tokens', op: 'scale', value: 1.5 }],
    relations: [report.relations.find((r) => r.target.region === 'copy').id],
    auditAlternatives: true
  };
  const result = Model.replay(report, input);
  const copy = result.alternativeChecks.find((r) => r.target.region === 'copy');
  assert.equal(copy.calls, 24);
  assert.equal(copy.disagreements, 24);
  assert.equal(copy.examples[0].selectedValue, 1.5 * copy.examples[0].alternativeValue);
  input.edits[0].value = 1;
  assert.ok(Model.replay(report, input).alternativeChecks.every((r) => r.disagreements === 0));
});

test('reported trace validity errors disable replay while preserving interface viewing', () => {
  const bad = clone();
  const events = bad.trace.events.slice(0, 2);
  events[0].seq = 1;
  events[0].end = 4;
  events[1].seq = 2;
  events[1].end = 5;
  events[1].thread = events[0].thread;
  bad.trace.events = events;
  bad.validity.traceErrors = ['crossing region boundaries on one thread'];
  bad.trace.complete = false;
  assert.doesNotThrow(() => Model.validate(bad));
  assert.throws(
    () =>
      Model.replay(bad, { edits: [{ region: 'enqueue', state: 'items', op: 'scale', value: 2 }] }),
    /validity errors/
  );
});
