/* Shared by the VS Code webview, extension host, and Node tests.
 * Scenario execution is a conditional replay of marker order, never timing.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports)
    module.exports = factory(require('./expressions'));
  else root.DrperfModel = factory(root.DrperfExpressions);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Expressions) {
  'use strict';
  const schema = 'drperf.explorer.v1';
  const compiledExpressions = new WeakMap();
  const childCostCache = new WeakMap();
  const id = (region, state) => JSON.stringify([region, state]);
  function keyFactory() {
    const regions = new Map();
    return (region, state) => {
      let states = regions.get(region);
      if (!states) {
        states = new Map();
        regions.set(region, states);
      }
      if (!states.has(state)) states.set(state, id(region, state));
      return states.get(state);
    };
  }
  const finite = (value) => typeof value === 'number' && Number.isFinite(value);
  const safe = (value) => Number.isSafeInteger(value);
  const sum = (values) => values.reduce((a, b) => a + b, 0);
  // Display precision must never change stored fits or scenario arithmetic.
  const coefficient = (value) => finite(value)
    ? new Intl.NumberFormat('en-US', { maximumFractionDigits: 0, useGrouping: false }).format(
      Math.round(value) || 0)
    : String(value);
  const format = (value) =>
    finite(value)
      ? new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.round(value) || 0)
      : String(value);

  function validate(model) {
    if (!model || model.schema !== schema)
      throw new Error(
        'Not a supported drperf explorer report. Export raw measurements with drperf-export.'
      );
    if (
      typeof model.id !== 'string' ||
      !model.id ||
      model.measurement?.unit !== 'CPU instructions per call' ||
      model.measurement?.scope !== 'exclusive region work'
    )
      throw new Error(
        'Unsupported report identity or measurement scope. The explorer requires exclusive CPU instructions per call.'
      );
    if (
      typeof model.trace?.complete !== 'boolean' ||
      !Array.isArray(model.validity?.errors) ||
      !Array.isArray(model.validity?.traceErrors) ||
      ![...model.validity.errors, ...model.validity.traceErrors].every(
        (error) => typeof error === 'string'
      ) ||
      (model.trace.recordCount !== undefined &&
        (!safe(model.trace.recordCount) || model.trace.recordCount < 0))
    )
      throw new Error('Invalid trace-completeness or measurement-validity metadata.');
    if (
      !Array.isArray(model.regions) ||
      !Array.isArray(model.relations) ||
      !Array.isArray(model.trace?.events)
    )
      throw new Error('Report is missing regions, relations, or trace events.');
    if (
      model.regions.length > 10000 ||
      model.relations.length > 100000 ||
      model.trace.events.length > 100000
    )
      throw new Error('Report exceeds viewer limits. Export fewer runs or lower the trace limit.');
    const integer = (x) => safe(x) || (typeof x === 'string' && /^[+-]?\d{1,128}$/.test(x));
    const names = new Map();
    const pointsValid = (points, n, fitted) =>
      Array.isArray(points) &&
      points.every(
        (p) =>
          p &&
          Array.isArray(p.state) &&
          p.state.length === n &&
          p.state.every(integer) &&
          safe(p.calls) &&
          p.calls >= 0 &&
          (fitted ? finite(p.explained) && finite(p.unexplained) : finite(p.observed))
      );
    for (const region of model.regions) {
      if (
        !region ||
        typeof region.id !== 'string' ||
        typeof region.name !== 'string' ||
        (region.originalName !== undefined && typeof region.originalName !== 'string') ||
        names.has(region.id) ||
        !Array.isArray(region.states) ||
        !region.states.every((s) => typeof s === 'string') ||
        new Set(region.states).size !== region.states.length ||
        !Array.isArray(region.regimes) ||
        (region.recordedRegimes !== undefined && !Array.isArray(region.recordedRegimes)) ||
        !Array.isArray(region.sources)
      )
        throw new Error('Invalid or duplicate region schema.');
      names.set(region.id, region);
      if (
        !safe(region.calls) ||
        region.calls < 0 ||
        !pointsValid(region.points, region.states.length, false)
      )
        throw new Error(`Invalid observations for ${region.name}.`);
      for (const source of region.sources)
        if (
          !source ||
          typeof source.path !== 'string' ||
          !safe(source.line) ||
          source.line < 1 ||
          !safe(source.endLine) ||
          source.endLine < source.line ||
          typeof source.sha256 !== 'string' ||
          (source.expressions !== undefined &&
            (!source.expressions ||
              typeof source.expressions !== 'object' ||
              Array.isArray(source.expressions) ||
              !Object.values(source.expressions).every((value) => typeof value === 'string')))
        )
          throw new Error('Invalid source location.');
      for (const fit of [...region.regimes, ...(region.recordedRegimes || [])]) {
        if (
          !fit ||
          !Array.isArray(fit.coefficients) ||
          fit.coefficients.length !== region.states.length ||
          !fit.coefficients.every(finite) ||
          !finite(fit.constant) ||
          !pointsValid(fit.points, region.states.length, true) ||
          !Array.isArray(fit.range) ||
          fit.range.length !== region.states.length ||
          !fit.range.every(
            (pair) =>
              Array.isArray(pair) &&
              pair.length === 2 &&
              pair.every(integer) &&
              asInteger(pair[0]) <= asInteger(pair[1])
          ) ||
          !Array.isArray(fit.dependent) ||
          !fit.dependent.every((s) => region.states.includes(s)) ||
          !finite(fit.unexplainedShare)
        )
          throw new Error(`Invalid formula for ${region.name}.`);
        const attribution = fit.attribution;
        if (
          !attribution ||
          !Array.isArray(attribution.coefficients) ||
          attribution.coefficients.length !== region.states.length ||
          ![...attribution.coefficients, attribution.constant, attribution.unexplained].every(
            (list) =>
              Array.isArray(list) &&
              list.every(
                (row) =>
                  row &&
                  typeof row.function === 'string' &&
                  typeof row.module === 'string' &&
                  finite(row.instructions)
              )
          )
        )
          throw new Error(`Invalid attribution for ${region.name}.`);
      }
    }
    const relationIds = new Set();
    validateComposition(model, names);
    for (const relation of model.relations) {
      if (
        !relation ||
        typeof relation.id !== 'string' ||
        relationIds.has(relation.id) ||
        !names.get(relation.target?.region)?.states.includes(relation.target?.state) ||
        !Array.isArray(relation.terms) ||
        relation.terms.length > 256 ||
        (!relation.terms.length && !relation.expression) ||
        !finite(relation.constant)
      )
        throw new Error('Invalid relationship.');
      relationIds.add(relation.id);
      for (const term of relation.terms) {
        if (
          !term ||
          !names.has(term.region) ||
          !['last', 'cum', 'cumend', 'count'].includes(term.kind) ||
          !finite(term.coefficient) ||
          (term.kind !== 'count' && !names.get(term.region).states.includes(term.state))
        )
          throw new Error('Invalid relationship term.');
        if (term.coefficientExact !== undefined) rational(term.coefficientExact);
      }
      if (relation.constantExact !== undefined) rational(relation.constantExact);
      if (relation.expression) {
        const compiled = Expressions.compile(relation.expression);
        const declared = new Set(
          relation.terms.map((t) => JSON.stringify([t.kind, t.region, t.state]))
        );
        if (
          compiled.features.length !== declared.size ||
          compiled.features.some((f) => !declared.has(JSON.stringify([f.kind, f.region, f.state])))
        )
          throw new Error('Expression dependencies do not match relationship terms.');
        compiledExpressions.set(relation, compiled);
      }
    }
    for (const event of model.trace.events)
      if (
        !event ||
        !names.has(event.region) ||
        typeof event.group !== 'string' ||
        typeof event.thread !== 'string' ||
        !safe(event.seq) ||
        !safe(event.end) ||
        event.end <= event.seq ||
        !event.values ||
        typeof event.values !== 'object' ||
        Array.isArray(event.values) ||
        !Object.values(event.values).every(integer)
      )
        throw new Error('Invalid trace event.');
    const markerIds = new Map(),
      stacks = new Map();
    if (!model.validity?.traceErrors?.length)
      for (const events of groupedEvents(model.trace.events))
        for (const event of events) {
          if (!markerIds.has(event.group)) markerIds.set(event.group, new Set());
          const used = markerIds.get(event.group);
          if (used.has(event.seq) || used.has(event.end))
            throw new Error('Duplicate marker sequence in trace.');
          used.add(event.seq);
          used.add(event.end);
          const thread = id(event.group, event.thread);
          if (!stacks.has(thread)) stacks.set(thread, []);
          const stack = stacks.get(thread);
          while (stack.length && stack.at(-1) < event.seq) stack.pop();
          if (stack.length && event.end > stack.at(-1))
            throw new Error('Crossing region boundaries on one thread.');
          stack.push(event.end);
        }
    return model;
  }

  function recordedCosts(model) {
    if (model.measurement?.markerAdjustment === 'none; marker API instructions retained')
      return model;
    const result = structuredClone(model);
    result.id = model.id + ':recorded';
    result.measurement = {
      ...model.measurement,
      markerAdjustment: 'none; marker API instructions retained'
    };
    for (const region of result.regions) {
      if (region.recordedRegimes) {
        region.regimes = structuredClone(region.recordedRegimes);
        region.markerCalibration = 0;
        for (const point of region.points) point.observed = point.recorded;
        region.diagnostics = (region.diagnostics || []).filter((message) => !/Marker|marker|calibrated explained/.test(message));
        continue;
      }
      const calibration = region.markerCalibration ?? region.regimes[0]?.markerCalibration ?? 0;
      for (const point of region.points)
        point.observed = point.recorded ?? point.observed + calibration;
      for (const fit of region.regimes) {
        const correction = fit.markerCalibration ?? calibration;
        fit.constant += correction;
        for (const point of fit.points) point.explained += correction;
        const total = sum(fit.points.map((p) => p.explained + p.unexplained));
        fit.unexplainedShare = total ? sum(fit.points.map((p) => p.unexplained)) / total : 0;
        fit.markerCalibration = 0;
      }
      region.markerCalibration = 0;
      region.diagnostics = (region.diagnostics || []).filter(
        (message) => !/Marker-overhead|calibrated explained/.test(message)
      );
    }
    if (result.composition) {
      result.composition = {
        ...result.composition,
        status: 'unavailable',
        regions: [],
        errors: ['Composition uses the original own-cost basis; open the original report for its symbolic interfaces.']
      };
    }
    return result;
  }

  function formula(region, fit = region.regimes[0]) {
    if (!fit) return 'More varied states needed';
    const terms = fit.coefficients.flatMap((value, i) =>
      value !== 0 ? [`${coefficient(value)}*${region.states[i]}`] : []
    );
    terms.push(coefficient(fit.constant));
    return (
      terms.join(' + ').replace(/\+ -/g, '- ') + (fit.blocks?.unexplained ? ' + unexplained' : '')
    );
  }

  function validateComposition(model, names) {
    const composition = model.composition;
    if (!composition) return;
    if (!['observed', 'unavailable'].includes(composition.status) ||
        !Array.isArray(composition.regions) || composition.regions.length > names.size)
      throw new Error('Invalid composition metadata.');
    const checkAffine = (relation, states) => {
      if (!relation || !Array.isArray(relation.coefficients) ||
          relation.coefficients.length !== states.length)
        throw new Error('Invalid child-call affine relation.');
      [...relation.coefficients, relation.constant].forEach(rational);
    };
    const seen = new Set();
    for (const parent of composition.regions) {
      const region = names.get(parent.id);
      if (!region || seen.has(parent.id) || !Array.isArray(parent.states) ||
          JSON.stringify(parent.states) !== JSON.stringify(region.states) ||
          !Array.isArray(parent.children) || parent.children.length > names.size)
        throw new Error('Invalid composed region.');
      seen.add(parent.id);
      const children = new Set();
      for (const edge of parent.children) {
        const child = names.get(edge.child);
        if (!child || children.has(edge.child) || !['product', 'sum', 'unresolved'].includes(edge.form) ||
            typeof edge.indexVariable !== 'string' || !edge.indexVariable ||
            !Array.isArray(edge.argumentStates) ||
            new Set(edge.argumentStates).size !== child.states.length ||
            edge.argumentStates.length !== child.states.length ||
            !edge.argumentStates.every((state) => child.states.includes(state)))
          throw new Error('Invalid composed child reference.');
        children.add(edge.child);
        if (edge.multiplicity !== null) checkAffine(edge.multiplicity, parent.states);
        for (const [field, states] of [['arguments', parent.states],
          ['sequenceArguments', [...parent.states, edge.indexVariable]]]) {
          const args = edge[field];
          if (args == null) continue;
          if (typeof args !== 'object' || Array.isArray(args) ||
              Object.keys(args).length !== child.states.length)
            throw new Error('Invalid composed child arguments.');
          edge.argumentStates.forEach((state) => checkAffine(args[state], states));
        }
        if (edge.form === 'product' && edge.multiplicity == null)
          throw new Error('A child product requires an affine multiplier.');
      }
    }
  }

  // Call counts and argument substitutions stay exact: fractions use integer
  // numerators/denominators instead of rounding away half a loop or an argument.
  function affineCallText(relation, states) {
    const exact = (value) => {
      const [n, d] = rational(value);
      return d === 1n ? String(n) : `${n}/${d}`;
    };
    const terms = relation.coefficients.flatMap((value, i) => {
      const text = exact(value);
      return rational(value)[0] === 0n ? [] : [text === '1' ? states[i] : `${text}*${states[i]}`];
    });
    if (rational(relation.constant)[0] !== 0n || !terms.length)
      terms.push(exact(relation.constant));
    return terms.join(' + ').replace(/\+ -/g, '- ');
  }

  function childTerms(model, regionId) {
    if (model.composition?.status !== 'observed') return [];
    const parent = model.composition.regions.find((region) => region.id === regionId);
    if (!parent) return [];
    return parent.children.map((edge) => {
      const count = edge.multiplicity ? affineCallText(edge.multiplicity, parent.states) : null;
      return { child: edge.child,
        prefix: count === null ? 'unexplained(' : (count === '1' ? '' : `(${count})*`),
        reference: `F[${edge.child}]`,
        suffix: count === null ? ')' : '' };
    });
  }

  // Reconstruct measured child-subtree work at the actual call sites. A state
  // bucket contains mean exclusive counts, not an exact per-invocation cost:
  // this is an estimate when the same state appears in different contexts.
  // The event tree (rather than recursively expanding region names) also handles
  // recursion and keeps grandchildren from being charged twice.
  function observedChildCosts(model) {
    if (childCostCache.has(model)) return childCostCache.get(model);
    const unavailable = (reason) => {
      const result = { reason, points: null };
      childCostCache.set(model, result);
      return result;
    };
    if (!model.trace?.complete || model.validity?.errors?.length || model.validity?.traceErrors?.length)
      return unavailable('Complete, valid call traces are required to account for child work.');
    const regions = new Map(model.regions.map((r) => [r.id, r]));
    const edges = new Map(model.composition.regions.map((r) =>
      [r.id, new Map(r.children.map((e) => [e.child, e]))]));
    const key = (state) => JSON.stringify(state.map(String));
    const points = new Map();
    for (const r of model.regions) {
      if (r.droppedCalls) return unavailable('Some region calls were omitted from the report.');
      const rows = new Map();
      for (const p of r.points) {
        if (!finite(p.observed) || p.observed < 0 || rows.has(key(p.state)))
          return unavailable('Child work has missing, negative, or duplicate state observations.');
        rows.set(key(p.state), { own: p.observed, expected: p.calls, calls: 0,
          childCost: 0, unresolvedCost: 0, children: new Map() });
      }
      if (sum(r.points.map((p) => p.calls)) !== r.calls)
        return unavailable('Region calls do not match state observations.');
      points.set(r.id, rows);
    }
    const nodes = [];
    for (const events of groupedEvents(model.trace.events)) {
      const stacks = new Map(), boundaries = new Set();
      for (const event of events) {
        const r = regions.get(event.region);
        if (!r || event.end <= event.seq || boundaries.has(event.seq) || boundaries.has(event.end) ||
            Object.keys(event.values).length !== r.states.length ||
            r.states.some((name) => !Object.hasOwn(event.values, name)))
          return unavailable('Invalid call boundaries or PCVs in the child trace.');
        boundaries.add(event.seq); boundaries.add(event.end);
        const row = points.get(r.id).get(key(r.states.map((name) => event.values[name])));
        if (!row) return unavailable('A child call has no matching measured state.');
        row.calls++;
        if (!stacks.has(event.thread)) stacks.set(event.thread, []);
        const stack = stacks.get(event.thread);
        while (stack.length && stack.at(-1).end < event.seq) stack.pop();
        const parent = stack.at(-1);
        if (parent && (event.end >= parent.end || !edges.get(parent.region)?.has(r.id)))
          return unavailable('Child composition does not match the recorded nesting.');
        const node = { region: r.id, end: event.end, row, parent, cost: row.own };
        nodes.push(node); stack.push(node);
      }
    }
    for (const rows of points.values())
      for (const row of rows.values())
        if (row.calls !== row.expected)
          return unavailable('Child traces do not cover all measured calls.');
    for (let i = nodes.length - 1; i >= 0; --i) {
      const node = nodes[i], parent = node.parent;
      if (!finite(node.cost)) return unavailable('Child instruction totals exceed numeric limits.');
      if (!parent) continue;
      parent.cost += node.cost;
      parent.row.childCost += node.cost;
      if (edges.get(parent.region).get(node.region).multiplicity == null) {
        parent.row.unresolvedCost += node.cost;
        parent.row.children.set(node.region, (parent.row.children.get(node.region) || 0) + node.cost);
      }
    }
    const result = { points, reason: null };
    childCostCache.set(model, result);
    return result;
  }

  function interfaceExplanation(model, regionId, fit) {
    const region = model.regions.find((r) => r.id === regionId);
    if (!region) throw new Error('Unknown region: ' + regionId);
    const parent = model.composition?.status === 'observed'
      ? model.composition.regions.find((r) => r.id === regionId) : null;
    const hasChildren = !!parent?.children.length;
    const selected = fit ? fit.points : region.regimes.length
      ? region.regimes.flatMap((f) => f.points)
      : region.points.map((p) => ({ ...p, explained: 0, unexplained: p.observed }));
    const unavailable = (reason) => ({ share: null, estimated: hasChildren, reason, children: [] });
    if (!selected.length) return unavailable('No measured states.');
    let total = 0, ownUnexplained = 0, unresolvedChildCost = 0;
    const children = new Map();
    const observed = hasChildren ? observedChildCosts(model) : null;
    if (observed?.reason) return unavailable(observed.reason);
    for (const p of selected) {
      if (!finite(p.explained) || !finite(p.unexplained) || p.explained < 0 || p.unexplained < 0)
        return unavailable('Negative or missing own-work costs cannot support this percentage.');
      total += p.explained + p.unexplained;
      ownUnexplained += p.unexplained;
      if (!hasChildren) continue;
      const row = observed.points.get(regionId).get(JSON.stringify(p.state.map(String)));
      if (!row?.calls) return unavailable('No matching calls for a fitted state.');
      total += row.childCost / row.calls;
      unresolvedChildCost += row.unresolvedCost / row.calls;
      for (const [child, cost] of row.children)
        children.set(child, (children.get(child) || 0) + cost / row.calls);
    }
    if (!finite(total) || !finite(ownUnexplained + unresolvedChildCost))
      return unavailable('Instruction totals exceed numeric limits.');
    // Preserve the fitter's equal weighting of distinct states. A resolved F is
    // an atomic explained term here, regardless of that child's own residuals.
    return { share: total ? (ownUnexplained + unresolvedChildCost) / total : 0,
      estimated: hasChildren, reason: null, ownUnexplained, unresolvedChildCost, total,
      children: [...children].map(([child, cost]) => ({ child, share: total ? cost / total : 0 })) };
  }

  function relationship(relation) {
    if (relation.expression)
      return `${relation.target.region}.${relation.target.state} = ${relation.expression}`;
    const terms = relation.terms.map(
      (term) =>
        `${term.coefficientExact || String(term.coefficient)}*${term.kind}(${term.region}${term.state === null ? '' : '.' + term.state})`
    );
    if (relation.constant) terms.push(relation.constantExact || String(relation.constant));
    return `${relation.target.region}.${relation.target.state} = ${terms.join(' + ').replace(/\+ -/g, '- ')}`;
  }

  function rational(value) {
    const text = String(value);
    if (text.length > 128) throw new Error('Exact coefficient is too large.');
    const fraction = /^([+-]?\d+)\/([1-9]\d*)$/.exec(text);
    if (fraction) return [BigInt(fraction[1]), BigInt(fraction[2])];
    const decimal = /^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(text);
    if (!decimal) throw new Error('Invalid exact relationship coefficient.');
    const exponent = Number(decimal[4] || 0) - (decimal[3] || '').length;
    if (Math.abs(exponent) > 308) throw new Error('Coefficient exponent is too large.');
    let n = BigInt((decimal[1] || '') + decimal[2] + (decimal[3] || '')),
      d = 1n;
    if (exponent >= 0) n *= 10n ** BigInt(exponent);
    else d = 10n ** BigInt(-exponent);
    return [n, d];
  }

  function asInteger(value) {
    if (typeof value === 'bigint') return value;
    if (safe(value)) return BigInt(value);
    if (typeof value === 'string' && /^[+-]?\d{1,128}$/.test(value)) return BigInt(value);
    throw new Error('State is not an exact integer.');
  }

  function exactRelationshipInteger(relation, featureValue) {
    if (relation.expression) {
      if (compiledExpressions.get(relation)?.source !== relation.expression)
        compiledExpressions.set(relation, Expressions.compile(relation.expression));
      return Expressions.evaluate(compiledExpressions.get(relation), featureValue);
    }
    let [n, d] = rational(relation.constantExact ?? relation.constant);
    for (const term of relation.terms) {
      const [tn, td] = rational(term.coefficientExact ?? term.coefficient);
      const x = featureValue(term);
      n = n * td + tn * asInteger(x) * d;
      d *= td;
    }
    if (n % d !== 0n)
      throw new Error(
        `Relationship produces a non-integer state for ${relation.target.region}.${relation.target.state}: ${n}/${d}. Revise this assumption or intervention.`
      );
    return n / d;
  }

  function exactRelationshipValue(relation, featureValue) {
    const value = Number(exactRelationshipInteger(relation, featureValue));
    if (!safe(value)) throw new Error('Relationship exceeds exact integer range.');
    return value;
  }

  function verifyRelationships(model, selectedIds = null) {
    const stateId = keyFactory();
    const chosen = model.relations.filter((r) => !selectedIds || selectedIds.includes(r.id));
    if (!chosen.length) return [];
    const results = new Map(
      chosen.map((r) => [r.id, { id: r.id, calls: 0, mismatches: 0, examples: [] }])
    );
    const byRegion = new Map();
    for (const relation of chosen) {
      if (!byRegion.has(relation.target.region)) byRegion.set(relation.target.region, []);
      byRegion.get(relation.target.region).push(relation);
    }
    const groups = new Map();
    for (const event of model.trace.events) {
      if (!groups.has(event.group)) groups.set(event.group, []);
      groups.get(event.group).push(event);
    }
    for (const [group, events] of groups) {
      events.sort((a, b) => a.seq - b.seq);
      const ended = [...events].sort((a, b) => a.end - b.end);
      const cum = new Map(),
        cumend = new Map(),
        last = new Map(),
        count = new Map();
      let ei = 0;
      for (const event of events) {
        while (ei < ended.length && ended[ei].end < event.seq) {
          const previous = ended[ei++];
          for (const [state, value] of Object.entries(previous.values)) {
            const key = stateId(previous.region, state);
            cumend.set(key, (cumend.get(key) || 0n) + asInteger(value));
          }
        }
        for (const relation of byRegion.get(event.region) || []) {
          if (!Object.hasOwn(event.values, relation.target.state)) continue;
          const result = results.get(relation.id);
          ++result.calls;
          let predicted,
            expected = asInteger(event.values[relation.target.state]);
          try {
            predicted = exactRelationshipInteger(relation, (term) => {
              if (term.kind === 'count') return count.get(term.region) || 0n;
              return (
                (term.kind === 'last' ? last : term.kind === 'cum' ? cum : cumend).get(
                  stateId(term.region, term.state)
                ) || 0n
              );
            });
          } catch (error) {
            predicted = error.message;
          }
          if (predicted !== expected) {
            ++result.mismatches;
            if (result.examples.length < 3)
              result.examples.push({
                group,
                seq: event.seq,
                expected: String(expected),
                predicted: String(predicted)
              });
          }
        }
        count.set(event.region, (count.get(event.region) || 0n) + 1n);
        for (const [state, value] of Object.entries(event.values)) {
          const key = stateId(event.region, state),
            x = asInteger(value);
          last.set(key, x);
          cum.set(key, (cum.get(key) || 0n) + x);
        }
      }
    }
    return [...results.values()].map((r) => ({ ...r, holds: r.calls > 0 && r.mismatches === 0 }));
  }

  function requireCompleteTrace(model) {
    if (model.validity?.errors?.length || model.validity?.traceErrors?.length)
      throw new Error('Measurement or trace validity errors disable scenario predictions.');
    if (!model.trace?.complete || !model.trace.events.length)
      throw new Error('A complete recorded trace is required for scenario replay.');
    if (
      model.trace.recordCount !== undefined &&
      model.trace.recordCount !== model.trace.events.length
    )
      throw new Error(
        'Trace event count differs from its completeness metadata. Re-export the raw measurements.'
      );
    const regions = new Map(model.regions.map((r) => [r.id, r]));
    const counts = new Map();
    for (const event of model.trace.events) {
      const region = regions.get(event.region),
        fields = Object.keys(event.values);
      if (
        !region ||
        fields.length !== region.states.length ||
        fields.some((state) => !region.states.includes(state))
      )
        throw new Error(
          'Trace PCV fields do not match the declared region interface. Re-export the raw measurements.'
        );
      counts.set(event.region, (counts.get(event.region) || 0) + 1);
    }
    for (const region of model.regions)
      if ((counts.get(region.id) || 0) !== region.calls)
        throw new Error(
          `Trace calls for ${region.id} differ from measured calls. Fixed-trace exploration requires complete matching measurements.`
        );
  }

  function proposeRelationship(model, target, expression) {
    requireCompleteTrace(model);
    if (!target || typeof target.region !== 'string' || typeof target.state !== 'string')
      throw new Error('Invalid proposal target.');
    const region = model.regions.find((r) => r.id === target.region);
    if (!region?.states.includes(target.state)) throw new Error('Unknown target PCV.');
    const compiled = Expressions.compile(expression);
    for (const feature of compiled.features) {
      const source = model.regions.find((r) => r.id === feature.region);
      if (!source || (feature.kind !== 'count' && !source.states.includes(feature.state)))
        throw new Error('Unknown history region or PCV in proposed relationship.');
    }
    const proposal = {
      id: 'proposed:' + JSON.stringify([target.region, target.state, expression]),
      target,
      expression,
      constant: 0,
      terms: compiled.features.map((f) => ({ ...f, coefficient: 1 })),
      proposed: true
    };
    compiledExpressions.set(proposal, compiled);
    const check = verifyRelationships({ ...model, relations: [proposal] })[0];
    proposal.evidence = {
      ...check,
      exact: check.holds,
      groups: new Set(model.trace.events.map((e) => e.group)).size
    };
    return { relation: proposal, check };
  }

  function withProposals(model, proposals) {
    if (!Array.isArray(proposals) || proposals.length > 100)
      throw new Error('At most 100 proposed relationships are supported.');
    if (!proposals.length) return model;
    const relations = [...model.relations],
      ids = new Set(relations.map((r) => r.id));
    for (const input of proposals) {
      const { relation, check } = proposeRelationship(model, input.target, input.expression);
      if (!check.holds)
        throw new Error(
          `Proposed relationship for ${input.target.region}.${input.target.state} fails at ${check.mismatches} recorded calls.`
        );
      if (!ids.has(relation.id)) {
        relations.push(relation);
        ids.add(relation.id);
      }
    }
    return { ...model, relations };
  }

  function evaluate(region, values) {
    const state = region.states.map((name) => values[name]);
    if (!state.every(safe))
      return { ok: false, reason: 'Missing state or integer outside JavaScript exact range' };
    if (!region.regimes.length) return { ok: false, reason: 'Insufficient observed states' };
    let fit, observed;
    for (const candidate of region.regimes) {
      const point = candidate.points.find(
        (p) => p.state.length === state.length && p.state.every((v, i) => v === state[i])
      );
      if (point) {
        fit = candidate;
        observed = point;
        break;
      }
    }
    const inRange = (candidate) =>
      candidate.range.every(
        ([lo, hi], i) => safe(lo) && safe(hi) && state[i] >= lo && state[i] <= hi
      );
    let support = observed ? 'observed' : 'unobserved';
    if (!fit) {
      const candidates = region.regimes.filter(inRange);
      if (candidates.length > 1)
        return {
          ok: false,
          reason: 'Overlapping fitted regimes; branch choice is ambiguous at this unobserved state'
        };
      fit = candidates[0];
    }
    if (!fit && region.regimes.length === 1) {
      fit = region.regimes[0];
      support = 'extrapolated';
    }
    if (!fit && state.length === 1) {
      const sorted = [...region.regimes].sort((a, b) => a.range[0][0] - b.range[0][0]);
      if (state[0] < sorted[0].range[0][0]) fit = sorted[0];
      else if (state[0] > sorted.at(-1).range[0][1]) fit = sorted.at(-1);
      if (fit) support = 'extrapolated';
    }
    if (!fit) return { ok: false, reason: 'Between fitted regimes; branch boundary is unknown' };
    if (!observed && fit.dependent.length)
      return { ok: false, reason: 'PCVs were correlated; this new state is not identifiable' };
    if (!observed && fit.range.some(([lo, hi], i) => lo === hi && state[i] !== lo))
      return { ok: false, reason: 'Changed a PCV that never varied in this regime' };
    const explained = sum(fit.coefficients.map((a, i) => a * state[i])) + fit.constant;
    if (!finite(explained) || explained < -1e-6)
      return { ok: false, reason: 'Formula predicts an invalid negative or non-finite cost' };
    return {
      ok: true,
      explained,
      support,
      fit,
      state,
      unexplained: observed ? observed.unexplained : null,
      hasUnexplained: !!fit.blocks?.unexplained
    };
  }

  function graph(model, relationIds = null) {
    const nodes = new Map(),
      edges = [];
    for (const region of model.regions)
      for (const state of region.states)
        nodes.set(id(region.id, state), { id: id(region.id, state), region: region.id, state });
    for (const relation of model.relations) {
      if (relationIds && !relationIds.includes(relation.id)) continue;
      const target = id(relation.target.region, relation.target.state);
      if (!nodes.has(target)) nodes.set(target, { id: target, ...relation.target });
      for (const term of relation.terms) {
        const source = id(term.region, term.state);
        if (!nodes.has(source))
          nodes.set(source, { id: source, region: term.region, state: term.state });
        edges.push({
          source,
          target,
          relation: relation.id,
          kind: term.kind,
          coefficient: term.coefficient
        });
      }
    }
    return { nodes: [...nodes.values()], edges };
  }

  function reachable(model, region, state, relationIds = null) {
    const { edges } = graph(model, relationIds),
      seen = new Set([id(region, state)]);
    let changed;
    do {
      changed = false;
      for (const edge of edges)
        if (seen.has(edge.source) && !seen.has(edge.target)) {
          seen.add(edge.target);
          changed = true;
        }
    } while (changed);
    return seen;
  }

  function replay(model, scenario, options = {}) {
    if (
      !scenario ||
      (scenario.edits !== undefined && !Array.isArray(scenario.edits)) ||
      (scenario.relations !== undefined && !Array.isArray(scenario.relations))
    )
      throw new Error('Invalid scenario.');
    if (
      scenario.costBasis !== undefined &&
      !['recorded', 'calibrated'].includes(scenario.costBasis)
    )
      throw new Error('Unknown scenario cost basis.');
    if ((scenario.edits?.length || 0) > 1000 || (scenario.relations?.length || 0) > 10000)
      throw new Error('Scenario exceeds the supported size.');
    const stateId = keyFactory();
    if (scenario.costBasis === 'recorded') model = recordedCosts(model);
    model = withProposals(model, scenario.proposals || []);
    validate(model);
    requireCompleteTrace(model);
    const regionMap = new Map(model.regions.map((r) => [r.id, r]));
    const selected = new Map();
    for (const selectedId of scenario.relations || []) {
      const relation = model.relations.find((r) => r.id === selectedId);
      if (!relation) throw new Error('Scenario refers to an unknown relationship.');
      const target = stateId(relation.target.region, relation.target.state);
      if (selected.has(target))
        throw new Error(
          `Choose one relationship for ${relation.target.region}.${relation.target.state}; alternatives are not interchangeable.`
        );
      selected.set(target, relation);
    }
    const selectedIds = new Set([...selected.values()].map((r) => r.id));
    const candidates = scenario.auditAlternatives
      ? model.relations.filter((r) => selected.has(stateId(r.target.region, r.target.state)))
      : [...selected.values()];
    const checks = verifyRelationships(
      model,
      candidates.map((r) => r.id)
    );
    const verified = new Set(checks.filter((c) => c.holds).map((c) => c.id));
    const invalidRelation = checks.find((check) => selectedIds.has(check.id) && !check.holds);
    if (invalidRelation)
      throw new Error(
        `Selected relationship ${invalidRelation.id} does not hold in the recorded trace. Inspect its counterexamples before using it.`
      );
    const alternatives = new Map(),
      ambiguities = new Map();
    if (scenario.auditAlternatives)
      for (const relation of candidates) {
        if (selectedIds.has(relation.id) || !verified.has(relation.id)) continue;
        const target = stateId(relation.target.region, relation.target.state);
        if (!alternatives.has(target)) alternatives.set(target, []);
        alternatives.get(target).push(relation);
        ambiguities.set(relation.id, {
          target: relation.target,
          selected: selected.get(target).id,
          candidate: relation.id,
          selectedEquation: relationship(selected.get(target)),
          candidateEquation: relationship(relation),
          calls: 0,
          disagreements: 0,
          examples: []
        });
      }
    const relationsByRegion = new Map();
    for (const [target, relation] of selected) {
      if (!relationsByRegion.has(relation.target.region))
        relationsByRegion.set(relation.target.region, []);
      relationsByRegion.get(relation.target.region).push([target, relation]);
    }
    const edits = new Map(),
      editsByRegion = new Map();
    for (const edit of scenario.edits || []) {
      if (
        !regionMap.get(edit.region)?.states.includes(edit.state) ||
        !['scale', 'add', 'set'].includes(edit.op) ||
        !finite(edit.value)
      )
        throw new Error('Invalid PCV intervention.');
      const key = stateId(edit.region, edit.state);
      if (edits.has(key)) throw new Error('Use one intervention per PCV.');
      edits.set(key, edit);
      if (!editsByRegion.has(edit.region)) editsByRegion.set(edit.region, []);
      editsByRegion.get(edit.region).push(edit);
    }
    if (!edits.size) throw new Error('Add at least one PCV intervention.');
    const summaries = new Map(
      model.regions.map((r) => [
        r.id,
        {
          region: r.id,
          calls: 0,
          changedCalls: 0,
          modelledCalls: 0,
          unknownCalls: 0,
          beforeSum: 0,
          afterSum: 0,
          changedStates: new Set(),
          reasons: new Set(),
          support: new Set(),
          unexplainedCalls: 0,
          unobservedBaselineCalls: 0,
          changes: []
        }
      ])
    );
    const warnings = new Set();
    const evaluations = new Map();
    const cachedEvaluation = (region, values) => {
      const key = JSON.stringify([region.id, region.states.map((state) => values[state])]);
      if (!evaluations.has(key)) evaluations.set(key, evaluate(region, values));
      return evaluations.get(key);
    };
    const predictedEvents = [];
    if (selected.size)
      warnings.add('Selected observed relationships are assumptions, not established causes.');
    warnings.add(
      'Call counts, nesting, and marker order are fixed. New branches/calls and elapsed time are not predicted.'
    );
    let group = null,
      cumulative,
      completed,
      latest,
      counts,
      pending;
    // End events are pre-sorted once per group; replayed values are filled at begin.
    const groups = new Map();
    for (const event of model.trace.events) {
      if (
        !regionMap.has(event.region) ||
        !safe(event.seq) ||
        !safe(event.end) ||
        event.end <= event.seq
      )
        throw new Error('Invalid trace event.');
      if (!groups.has(event.group)) groups.set(event.group, []);
      groups.get(event.group).push(event);
    }
    for (const [name, events] of groups) {
      group = name;
      cumulative = new Map();
      completed = new Map();
      latest = new Map();
      counts = new Map();
      pending = new Map();
      events.sort((a, b) => a.seq - b.seq);
      const ended = [...events].sort((a, b) => a.end - b.end);
      let endIndex = 0,
        lastSeq = -1;
      for (const event of events) {
        if (event.seq === lastSeq) throw new Error('Duplicate begin sequence in trace.');
        lastSeq = event.seq;
        while (endIndex < ended.length && ended[endIndex].end < event.seq) {
          const endedEvent = ended[endIndex++],
            values = pending.get(endedEvent.seq);
          if (!values) throw new Error('End event without a preceding begin event.');
          for (const [state, value] of Object.entries(values)) {
            const key = stateId(endedEvent.region, state);
            const next = (completed.get(key) || 0) + value;
            if (!safe(next))
              throw new Error('Scenario cumulative state exceeds exact integer range.');
            completed.set(key, next);
          }
        }
        const values = Object.assign(Object.create(null), event.values);
        for (const value of Object.values(values))
          if (!safe(value))
            throw new Error(
              'Trace contains state values outside JavaScript exact integer range. Values remain viewable, but replay is disabled.'
            );
        const derivations = [];
        const keepDerivations = summaries.get(event.region).changes.length < 8;
        for (const [target, relation] of relationsByRegion.get(event.region) || []) {
          const inputs = [];
          const feature = (term) =>
            term.kind === 'count'
              ? counts.get(term.region) || 0
              : (term.kind === 'last' ? latest : term.kind === 'cum' ? cumulative : completed).get(
                  stateId(term.region, term.state)
                ) || 0;
          const value = exactRelationshipValue(relation, (term) => {
            const history = feature(term);
            if (keepDerivations)
              inputs.push({
                kind: term.kind,
                region: term.region,
                state: term.state,
                value: history
              });
            return history;
          });
          for (const alternative of alternatives.get(target) || []) {
            const row = ambiguities.get(alternative.id);
            ++row.calls;
            let prediction;
            try {
              prediction = exactRelationshipValue(alternative, feature);
            } catch (error) {
              prediction = error.message;
            }
            if (prediction !== value) {
              ++row.disagreements;
              if (row.examples.length < 3)
                row.examples.push({
                  group,
                  seq: event.seq,
                  selectedValue: value,
                  alternativeValue: prediction
                });
            }
          }
          if (keepDerivations)
            derivations.push({
              state: relation.target.state,
              relationship: relation.id,
              equation: relationship(relation),
              inputs,
              result: value
            });
          values[relation.target.state] = value;
          if (edits.has(target))
            warnings.add(
              `Direct intervention overrides the relationship for ${relation.target.region}.${relation.target.state}.`
            );
        }
        for (const edit of editsByRegion.get(event.region) || []) {
          const before = values[edit.state];
          values[edit.state] =
            edit.op === 'scale'
              ? before * edit.value
              : edit.op === 'add'
                ? before + edit.value
                : edit.value;
          if (!safe(values[edit.state]))
            throw new Error('Intervention must produce exact integer PCV values.');
          if (keepDerivations)
            derivations.push({
              state: edit.state,
              intervention: edit.op,
              value: edit.value,
              before,
              result: values[edit.state]
            });
        }
        const region = regionMap.get(event.region),
          summary = summaries.get(event.region);
        ++summary.calls;
        const changed = region.states.filter((state) => values[state] !== event.values[state]);
        if (changed.length) {
          ++summary.changedCalls;
          changed.forEach((state) => summary.changedStates.add(state));
          if (summary.changes.length < 8)
            summary.changes.push({
              group,
              seq: event.seq,
              before: event.values,
              after: values,
              derivations: derivations.filter((d) => changed.includes(d.state))
            });
        }
        const before = cachedEvaluation(region, event.values),
          after = cachedEvaluation(region, values);
        if (before.ok && after.ok) {
          ++summary.modelledCalls;
          summary.beforeSum += before.explained;
          summary.afterSum += after.explained;
          summary.support.add(after.support);
          if (before.support !== 'observed') ++summary.unobservedBaselineCalls;
          if (before.hasUnexplained || after.hasUnexplained) ++summary.unexplainedCalls;
        } else {
          ++summary.unknownCalls;
          summary.reasons.add(!before.ok ? before.reason : after.reason);
        }
        pending.set(event.seq, values);
        if (options.includeTrace) predictedEvents.push({ ...event, values });
        counts.set(event.region, (counts.get(event.region) || 0) + 1);
        for (const [state, value] of Object.entries(values)) {
          const key = stateId(event.region, state),
            next = (cumulative.get(key) || 0) + value;
          if (!safe(next))
            throw new Error('Scenario cumulative state exceeds exact integer range.');
          cumulative.set(key, next);
          latest.set(key, value);
        }
      }
    }
    return {
      modelId: model.id,
      scenario,
      warnings: [...warnings],
      ...(scenario.auditAlternatives
        ? {
            alternativeChecks: [...ambiguities.values()],
            alternativeContract:
              'One-step comparisons in the selected scenario history, before direct target overrides; not measurements or full replays under each alternative.'
          }
        : {}),
      ...(options.includeTrace ? { predictedEvents } : {}),
      regions: [...summaries.values()].map((s) => ({
        region: s.region,
        calls: s.calls,
        changedCalls: s.changedCalls,
        modelledCalls: s.modelledCalls,
        unknownCalls: s.unknownCalls,
        changedStates: [...s.changedStates],
        support: [...s.support],
        reasons: [...s.reasons],
        unexplainedCalls: s.unexplainedCalls,
        unobservedBaselineCalls: s.unobservedBaselineCalls,
        changes: s.changes,
        before: s.modelledCalls ? s.beforeSum / s.modelledCalls : null,
        after: s.modelledCalls ? s.afterSum / s.modelledCalls : null,
        delta: s.modelledCalls ? (s.afterSum - s.beforeSum) / s.modelledCalls : null
      }))
    };
  }

  function groupedEvents(events) {
    const groups = new Map();
    for (const event of events) {
      if (!groups.has(event.group)) groups.set(event.group, []);
      groups.get(event.group).push(event);
    }
    return [...groups.values()].map((group) => [...group].sort((a, b) => a.seq - b.seq));
  }

  function traceStructure(events) {
    return groupedEvents(events).map((group) => {
      const threads = new Map();
      const ordered = [...group].sort((a, b) => a.seq - b.seq);
      const markers = [];
      ordered.forEach((event, i) => {
        if (!threads.has(event.thread)) threads.set(event.thread, threads.size);
        markers.push([event.seq, 'begin', event.region, i, threads.get(event.thread)]);
        markers.push([event.end, 'end', event.region, i, threads.get(event.thread)]);
      });
      return markers.sort((a, b) => a[0] - b[0]).map((m) => m.slice(1));
    });
  }

  function measurementSignature(report) {
    const fields = [
      'version',
      'follow_unmarked_threads',
      'native_gx',
      'excluded_cuda_module',
      'rep_expand'
    ];
    const settings = (report.provenance?.runs || []).map((run) =>
      fields.map((key) => run.measurement?.[key] ?? null)
    );
    return JSON.stringify({
      unit: report.measurement?.unit,
      scope: report.measurement?.scope,
      markerAdjustment: report.measurement?.markerAdjustment,
      settings: [...new Set(settings.map((s) => JSON.stringify(s)))].sort()
    });
  }

  function validateScenario(model, scenario, measured) {
    if (scenario.costBasis === 'recorded') {
      model = recordedCosts(model);
      measured = recordedCosts(measured);
    }
    validate(measured);
    requireCompleteTrace(measured);
    if (
      measured.validity?.errors?.length ||
      measured.validity?.traceErrors?.length ||
      !measured.trace.complete
    )
      throw new Error('Validation report must have a complete, valid trace.');
    if (measurementSignature(model) !== measurementSignature(measured))
      throw new Error('Measurement scope or instrumentation settings differ between reports.');
    const prediction = replay(model, scenario, { includeTrace: true });
    if (
      JSON.stringify(traceStructure(model.trace.events)) !==
      JSON.stringify(traceStructure(measured.trace.events))
    ) {
      return {
        modelId: model.id,
        measuredModelId: measured.id,
        structureMatches: false,
        regions: [],
        reason:
          'Recorded call count, marker order, thread roles, or nesting changed. Fixed-trace scenario validation is not applicable.'
      };
    }
    const actualRegions = new Map(measured.regions.map((r) => [r.id, r]));
    const originalRegions = new Map(model.regions.map((r) => [r.id, r]));
    const summaries = new Map();
    const events = groupedEvents(measured.trace.events).flat();
    const predicted = groupedEvents(prediction.predictedEvents).flat();
    for (let i = 0; i < predicted.length; ++i) {
      const event = predicted[i],
        actual = events[i],
        original = originalRegions.get(event.region),
        measuredRegion = actualRegions.get(event.region);
      if (!summaries.has(event.region))
        summaries.set(event.region, {
          region: event.region,
          calls: 0,
          stateMatches: 0,
          costChecks: 0,
          unknownCosts: 0,
          absoluteError: 0,
          observedSum: 0,
          predictedSum: 0,
          examples: []
        });
      const summary = summaries.get(event.region);
      ++summary.calls;
      const matches =
        original.states.length === measuredRegion.states.length &&
        original.states.every(
          (state) =>
            measuredRegion.states.includes(state) &&
            String(event.values[state]) === String(actual.values[state])
        );
      if (matches) ++summary.stateMatches;
      else if (summary.examples.length < 3)
        summary.examples.push({ kind: 'state', predicted: event.values, measured: actual.values });
      const fitted = evaluate(original, event.values);
      const point = measuredRegion.points.find((point) =>
        point.state.every((v, j) => String(v) === String(actual.values[measuredRegion.states[j]]))
      );
      // A partial explained formula must not be compared to full observed cost.
      if (!matches || !fitted.ok || fitted.hasUnexplained || !point || !finite(point.observed)) {
        ++summary.unknownCosts;
        continue;
      }
      ++summary.costChecks;
      summary.absoluteError += Math.abs(fitted.explained - point.observed);
      summary.observedSum += point.observed;
      summary.predictedSum += fitted.explained;
      if (
        Math.abs(fitted.explained - point.observed) >
          Math.max(64, Math.abs(point.observed) * 0.05) &&
        summary.examples.length < 3
      )
        summary.examples.push({
          kind: 'cost',
          states: actual.values,
          predicted: fitted.explained,
          measured: point.observed,
          support: fitted.support
        });
    }
    return {
      modelId: model.id,
      measuredModelId: measured.id,
      structureMatches: true,
      comparison:
        'Changed-run observed per-state means versus baseline-formula predictions; excludes predictions with unexplained blocks.',
      regions: [...summaries.values()].map((row) => ({
        region: row.region,
        calls: row.calls,
        stateMatches: row.stateMatches,
        costChecks: row.costChecks,
        unknownCosts: row.unknownCosts,
        meanPredicted: row.costChecks ? row.predictedSum / row.costChecks : null,
        meanObserved: row.costChecks ? row.observedSum / row.costChecks : null,
        meanAbsoluteError: row.costChecks ? row.absoluteError / row.costChecks : null,
        relativeAbsoluteError:
          row.costChecks && row.observedSum > 0 ? row.absoluteError / row.observedSum : null,
        examples: row.examples
      }))
    };
  }

  function compareInterfaces(before, after, options = {}) {
    if (options.costBasis === 'recorded') {
      before = recordedCosts(before);
      after = recordedCosts(after);
    }
    validate(before);
    validate(after);
    if (before.validity?.errors?.length || after.validity?.errors?.length)
      throw new Error('Invalid instruction measurements cannot support an interface comparison.');
    if (measurementSignature(before) !== measurementSignature(after))
      throw new Error('Measurement scope or instrumentation settings differ between reports.');
    // A schema variant can appear when a later report has additional marker
    // schemas. Match by original name + PCV names, not by display text or order.
    const key = (region) =>
      JSON.stringify([region.originalName || region.id, [...region.states].sort()]);
    const index = (report) => {
      const out = new Map();
      for (const region of report.regions) {
        const k = key(region);
        if (out.has(k)) throw new Error('Ambiguous interface identity in comparison.');
        out.set(k, region);
      }
      return out;
    };
    const left = index(before),
      right = index(after),
      rows = [];
    for (const identity of new Set([...left.keys(), ...right.keys()])) {
      const a = left.get(identity),
        b = right.get(identity);
      if (!a || !b) {
        rows.push({
          region: (a || b).id,
          name: (a || b).name,
          status: a ? 'only-before' : 'only-after',
          pairedStates: 0,
          points: []
        });
        continue;
      }
      const order = b.states.map((state) => a.states.indexOf(state));
      const bPoints = new Map(
        b.points.map((point) => {
          const aligned = Array(a.states.length);
          point.state.forEach((value, i) => (aligned[order[i]] = String(value)));
          return [JSON.stringify(aligned), point];
        })
      );
      const points = [];
      let unsupported = 0;
      for (const point of a.points) {
        const other = bPoints.get(JSON.stringify(point.state.map(String)));
        if (!other) continue;
        if (point.observed < 0 || other.observed < 0) {
          ++unsupported;
          continue;
        }
        points.push({
          state: point.state,
          before: point.observed,
          after: other.observed,
          delta: other.observed - point.observed,
          beforeCalls: point.calls,
          afterCalls: other.calls
        });
      }
      const beforeMean = points.length ? sum(points.map((p) => p.before)) / points.length : null;
      const afterMean = points.length ? sum(points.map((p) => p.after)) / points.length : null;
      const changes = [];
      let coefficientNote =
        'Coefficient changes need one identifiable fitted regime in both reports.';
      if (
        a.regimes.length === 1 &&
        b.regimes.length === 1 &&
        !a.regimes[0].dependent.length &&
        !b.regimes[0].dependent.length
      ) {
        for (const state of a.states) {
          const ai = a.states.indexOf(state),
            bi = b.states.indexOf(state);
          const af = a.regimes[0],
            bf = b.regimes[0];
          if (af.range[ai][0] === af.range[ai][1] || bf.range[bi][0] === bf.range[bi][1]) continue;
          const av = af.coefficients[ai],
            bv = bf.coefficients[bi];
          const difference =
            Math.abs(bv - av) <= 1e-9 * Math.max(1, Math.abs(av), Math.abs(bv)) ? 0 : bv - av;
          changes.push({ state, before: av, after: bv, delta: difference });
        }
        coefficientNote =
          'Coefficient comparisons describe the fitted observations; differing state coverage can change a fitted slope without a code regression.';
      }
      const expressions = (region) => {
        const out = Object.create(null);
        for (const source of region.sources)
          for (const [name, text] of Object.entries(source.expressions || {})) {
            if (!out[name]) out[name] = [];
            if (!out[name].includes(text)) out[name].push(text);
          }
        return out;
      };
      const ae = expressions(a),
        be = expressions(b);
      const changedExpressions = a.states.filter(
        (state) =>
          ae[state] &&
          be[state] &&
          JSON.stringify(ae[state].sort()) !== JSON.stringify(be[state].sort())
      );
      rows.push({
        region: a.id,
        afterRegion: b.id,
        name: a.name,
        states: a.states,
        status: points.length ? 'paired' : 'no-common-states',
        pairedStates: points.length,
        beforeStates: a.points.length,
        afterStates: b.points.length,
        unsupportedStates: unsupported,
        beforeMean,
        afterMean,
        deltaMean: points.length ? afterMean - beforeMean : null,
        relativeDelta: beforeMean > 0 ? (afterMean - beforeMean) / beforeMean : null,
        coefficientChanges: changes,
        coefficientNote,
        changedExpressions,
        beforeFormulas: a.regimes.map((f) => formula(a, f)),
        afterFormulas: b.regimes.map((f) => formula(b, f)),
        points
      });
    }
    return {
      schema: 'drperf.comparison.v1',
      beforeModelId: before.id,
      afterModelId: after.id,
      basis:
        'Observed per-state means at exactly shared PCV states, weighted equally across states within each region.',
      assumptions: [
        'PCV names retain their semantic meaning across reports.',
        'Differences are measurements, not a significance test or a latency prediction.'
      ],
      regions: rows
    };
  }

  function checkRelationships(reference, measured, options = {}) {
    validate(reference);
    validate(measured);
    requireCompleteTrace(reference);
    requireCompleteTrace(measured);
    const originalId = reference.id;
    reference = withProposals(reference, options.proposals || []);
    if (options.relations !== undefined && !Array.isArray(options.relations))
      throw new Error('Relationship selection must be an array.');
    const selected =
      options.relations === undefined
        ? reference.relations
        : options.relations.map((relationId) => {
            const relation = reference.relations.find((r) => r.id === relationId);
            if (!relation) throw new Error('Unknown relationship to check.');
            return relation;
          });
    const identity = (region) =>
      JSON.stringify([region.originalName || region.id, [...region.states].sort()]);
    const index = new Map();
    for (const region of measured.regions) {
      const key = identity(region);
      if (index.has(key)) throw new Error('Ambiguous measured interface identity.');
      index.set(key, region);
    }
    const correspondence = new Map(),
      reverse = new Map();
    for (const region of reference.regions) {
      const match = index.get(identity(region));
      if (match) {
        if (reverse.has(match.id)) throw new Error('Ambiguous reference interface identity.');
        correspondence.set(region.id, match);
        reverse.set(match.id, region.id);
      }
    }
    // Preserve measured marker order and per-run history. Unrelated regions can
    // be omitted because none of these equations refers to their history.
    const events = measured.trace.events
      .filter((e) => reverse.has(e.region))
      .map((e) => ({ ...e, region: reverse.get(e.region) }));
    const baseline = new Map(
      verifyRelationships(
        reference,
        selected.map((r) => r.id)
      ).map((check) => [check.id, check])
    );
    const available = selected.filter(
      (r) =>
        correspondence.has(r.target.region) && r.terms.every((t) => correspondence.has(t.region))
    );
    const checked = new Map(
      verifyRelationships(
        { relations: available, trace: { events } },
        available.map((r) => r.id)
      ).map((check) => [check.id, check])
    );
    const referenceRegions = new Map(reference.regions.map((r) => [r.id, r]));
    const sourceExpressions = (region, state) =>
      [
        ...new Set(
          region.sources.flatMap((source) =>
            Object.hasOwn(source.expressions || {}, state) ? [source.expressions[state]] : []
          )
        )
      ].sort();
    const checks = selected.map((relation) => {
      const original = baseline.get(relation.id),
        current = checked.get(relation.id);
      const dependencies = [
        relation.target,
        ...relation.terms.map((t) => ({
          region: t.region,
          state: t.kind === 'count' ? null : t.state
        }))
      ];
      const missing = [
        ...new Set(dependencies.filter((t) => !correspondence.has(t.region)).map((t) => t.region))
      ];
      const changedExpressions = [];
      const seen = new Set();
      for (const dependency of dependencies) {
        const key = id(dependency.region, dependency.state);
        if (seen.has(key) || dependency.state === null || !correspondence.has(dependency.region))
          continue;
        seen.add(key);
        const before = sourceExpressions(referenceRegions.get(dependency.region), dependency.state);
        const after = sourceExpressions(correspondence.get(dependency.region), dependency.state);
        if (before.length && after.length && JSON.stringify(before) !== JSON.stringify(after))
          changedExpressions.push(dependency);
      }
      return {
        id: relation.id,
        target: relation.target,
        equation: relationship(relation),
        baseline: original,
        status: !original.holds
          ? 'baseline-failed'
          : missing.length
            ? 'unavailable'
            : !current?.calls
              ? 'not-exercised'
              : current.holds
                ? 'holds'
                : 'fails',
        measured: current || null,
        missing,
        changedExpressions
      };
    });
    return {
      schema: 'drperf.relationship-check.v1',
      referenceModelId: originalId,
      measuredModelId: measured.id,
      contract:
        'State equations are checked against actual history in each measured process/run. Call counts, nesting, and ordering may differ. Matching PCV names and schemas must retain their semantic meaning. Agreement is observational, not causal proof; no cost or latency is predicted.',
      checks,
      summary: Object.fromEntries(
        ['holds', 'fails', 'baseline-failed', 'unavailable', 'not-exercised'].map((status) => [
          status,
          checks.filter((c) => c.status === status).length
        ])
      )
    };
  }

  function findDistinguishingExperiments(model, assumptions, options = {}) {
    const maxProbes = options.maxProbes ?? 12;
    if (!safe(maxProbes) || maxProbes < 1 || maxProbes > 64)
      throw new Error('Experiment search supports 1 to 64 probes.');
    if (!assumptions || !Array.isArray(assumptions.relations) || !assumptions.relations.length)
      throw new Error('Choose relationship assumptions before searching for experiments.');
    if (assumptions.edits?.length)
      throw new Error(
        'Experiment search starts from the recorded baseline; omit existing interventions.'
      );
    if (
      assumptions.costBasis !== undefined &&
      !['recorded', 'calibrated'].includes(assumptions.costBasis)
    )
      throw new Error('Unknown scenario cost basis.');
    if (
      !model.trace?.complete ||
      !model.trace.events.length ||
      model.validity?.errors?.length ||
      model.validity?.traceErrors?.length
    )
      throw new Error('Experiment search requires a complete, valid recorded trace.');
    const original = model;
    if (assumptions.costBasis === 'recorded') model = recordedCosts(model);
    model = withProposals(model, assumptions.proposals || []);
    validate(model);
    requireCompleteTrace(model);
    const selected = new Map();
    for (const relationId of assumptions.relations) {
      const relation = model.relations.find((r) => r.id === relationId);
      if (!relation) throw new Error('Unknown relationship assumption.');
      const key = id(relation.target.region, relation.target.state);
      if (selected.has(key)) throw new Error('Choose one relationship per target PCV.');
      selected.set(key, relation);
    }
    const candidates = model.relations.filter((r) =>
      selected.has(id(r.target.region, r.target.state))
    );
    const checks = verifyRelationships(
      model,
      candidates.map((r) => r.id)
    );
    const verified = new Set(checks.filter((c) => c.holds).map((c) => c.id));
    if ([...selected.values()].some((r) => !verified.has(r.id)))
      throw new Error('A selected relationship does not hold in the recorded trace.');
    const ambiguous = new Map();
    for (const r of candidates) {
      const key = id(r.target.region, r.target.state);
      if (verified.has(r.id) && r.id !== selected.get(key).id) {
        if (!ambiguous.has(key)) ambiguous.set(key, [selected.get(key)]);
        ambiguous.get(key).push(r);
      }
    }
    const inputs = new Map();
    for (const [target, relations] of ambiguous)
      for (const relation of relations) {
        for (const term of relation.terms) {
          if (term.kind === 'count' || (!relation.expression && term.coefficient === 0)) continue;
          const key = id(term.region, term.state);
          if (key === target) continue;
          if (!inputs.has(key))
            inputs.set(key, { region: term.region, state: term.state, targets: new Set() });
          inputs.get(key).targets.add(target);
        }
      }
    const sources = [...inputs.values()].sort(
      (a, b) =>
        b.targets.size - a.targets.size ||
        id(a.region, a.state).localeCompare(id(b.region, b.state))
    );
    const probes = sources.flatMap((source) => [
      { region: source.region, state: source.state, op: 'add', value: 1 },
      { region: source.region, state: source.state, op: 'scale', value: 2 }
    ]);
    const suggestions = [],
      rejected = [];
    let tried = 0;
    for (const edit of probes.slice(0, maxProbes)) {
      ++tried;
      const scenario = {
        relations: assumptions.relations,
        proposals: assumptions.proposals || [],
        costBasis: assumptions.costBasis || 'calibrated',
        edits: [edit],
        auditAlternatives: true
      };
      try {
        // Proposals were already checked above. Keeping them in the exported
        // scenario still makes each suggestion independently replayable.
        const result = replay(model, { ...scenario, proposals: [] });
        const disagreements = result.alternativeChecks.filter(
          (check) =>
            check.disagreements &&
            id(check.target.region, check.target.state) !== id(edit.region, edit.state)
        );
        if (!disagreements.length) continue;
        const targets = [
          ...new Map(
            disagreements.map((check) => [
              id(check.target.region, check.target.state),
              check.target
            ])
          ).values()
        ];
        suggestions.push({
          edit,
          scenario,
          targets,
          disagreements,
          changedRegions: result.regions
            .filter((r) => r.changedCalls)
            .map((r) => ({
              region: r.region,
              calls: r.calls,
              changedCalls: r.changedCalls,
              modelledCalls: r.modelledCalls,
              unknownCalls: r.unknownCalls,
              support: r.support,
              unexplainedCalls: r.unexplainedCalls
            }))
        });
      } catch (error) {
        rejected.push({ edit, reason: error.message });
      }
    }
    suggestions.sort(
      (a, b) =>
        b.targets.length - a.targets.length || b.disagreements.length - a.disagreements.length
    );
    return {
      schema: 'drperf.experiments.v1',
      modelId: original.id,
      assumptions: {
        relations: assumptions.relations,
        proposals: assumptions.proposals || [],
        costBasis: assumptions.costBasis || 'calibrated'
      },
      contract:
        'Candidate single-PCV interventions from the recorded baseline under selected assumptions. Differences are one-step equation disagreements, not causal evidence. Realizable program inputs must be supplied and measured separately. Call structure stays fixed.',
      search: {
        possibleProbes: probes.length,
        tried,
        maxProbes,
        truncated: probes.length > tried,
        ambiguousTargets: ambiguous.size,
        operations: ['add 1', 'multiply by 2']
      },
      suggestions,
      rejected
    };
  }

  function suggestedExperiments(model, region) {
    const suggestions = [];
    if (!region.regimes.length)
      suggestions.push('Exercise more distinct PCV states before fitting a formula.');
    for (const fit of region.regimes) {
      if (fit.dependent.length)
        suggestions.push(
          `Vary ${fit.dependent.join(', ')} independently to separate their coefficients.`
        );
      if (fit.unexplainedShare > 0.05)
        suggestions.push(
          'Inspect unexplained-function attribution; add a missing semantic PCV or split the region, then rerun small cases.'
        );
      for (let i = 0; i < fit.range.length; ++i)
        if (fit.range[i][0] === fit.range[i][1])
          suggestions.push(`Vary ${region.states[i]}: it was constant in this regime.`);
    }
    if (region.regimes.length > 1)
      suggestions.push('Probe the gap between fitted regimes to locate the branch transition.');
    const related = model.relations.filter((r) => r.target.region === region.id);
    if (related.length)
      suggestions.push(
        'Perturb a source PCV in a small execution and check whether the observed relationship survives.'
      );
    if (!suggestions.length)
      suggestions.push(
        'Hold other PCVs fixed and test a new small state to challenge the formula outside its observed points.'
      );
    return [...new Set(suggestions)];
  }

  return {
    schema,
    id,
    validate,
    format,
    formula,
    childTerms,
    interfaceExplanation,
    relationship,
    evaluate,
    graph,
    reachable,
    replay,
    suggestedExperiments,
    exactRelationshipValue,
    verifyRelationships,
    validateScenario,
    proposeRelationship,
    withProposals,
    recordedCosts,
    compareInterfaces,
    findDistinguishingExperiments,
    checkRelationships
  };
});
