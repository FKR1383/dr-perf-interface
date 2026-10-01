/* No report data is inserted as HTML. All names, formulas, and source text are
 * rendered with textContent; report expressions are never evaluated as code. */
(function () {
  'use strict';
  const M = window.DrperfModel;
  const G = window.DrperfGraph;
  const graphHistory = [];
  const graphLayouts=new Map();
  let graphShowSequence=false, graphDetailsOpen=false, graphSidebarOpen=false, graphAutoFit=true;
  let graphToggleFocus=null, graphLayoutRequest=null;
  const graphExpanded = new Set();
  let graphHighlight = null;
  let graphZoom = 1, graphViewportKey = null;
  let graphFullscreen = !!window.DrperfStandalone, graphMode = 'top', renderedTab = null;
  const analysis = window.DrperfAnalysis;
  let scenarioImportGeneration = 0;
  let scenarioGeneration = 0,
    scenarioPending = false,
    scenarioCache = null,
    comparisonCache = null,
    proposalModelCache = null;
  let scenarioValidation = null,
    scenarioValidationError = '';
  let experimentCache = null;
  let relationshipCheckCache = null;
  const host = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null;
  const saved = host?.getState() || {};
  const sourceStatuses = new Map();
  let loadedModel = null,
    rawCosts = saved.rawCosts || false;
  let model = null,
    selected = null,
    activeTab = window.DrperfStandalone ? 'graph' : saved.tab || 'interface',
    filter = '',
    result = null;
  let edits = [],
    assumptionIds = [],
    scenarioError = '',
    onlyAffected = true;
  let validationModel = null,
    validationName = '';
  let auditAlternatives = saved.auditAlternatives || false;
  let proposals = [],
    proposalDraft = null,
    proposalResult = null;
  const scenarioModel = () => {
    const key = JSON.stringify(proposals);
    if (proposalModelCache?.model !== model || proposalModelCache.key !== key)
      proposalModelCache = { model, key, value: M.withProposals(model, proposals) };
    return proposalModelCache.value;
  };
  const root = document.getElementById('app');
  const send = (message) =>
    host
      ? host.postMessage(message)
      : window.dispatchEvent(new CustomEvent('drperfHostMessage', { detail: message }));
  const el = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const button = (text, action, className = '') => {
    const b = el('button', className, text);
    b.type = 'button';
    b.addEventListener('click', action);
    return b;
  };
  const append = (parent, ...children) => {
    children.filter(Boolean).forEach((child) => parent.append(child));
    return parent;
  };
  const fmt = M.format;
  const region = () => model?.regions.find((r) => r.id === selected) || model?.regions[0];
  const badge = (text, tone = '') => el('span', 'badge ' + tone, text);
  const stateLabel = (names, values) => names.map((name, i) => `${name}=${values[i]}`).join(', ');
  const persist = () =>
    host?.setState({
      modelId: model?.id,
      selected,
      tab: activeTab,
      edits,
      assumptionIds,
      proposals,
      rawCosts,
      auditAlternatives
    });
  function choose(id, tab = activeTab) {
    if (tab === 'graph' && selected && selected !== id) graphHistory.push(selected);
    selected = id;
    activeTab = tab;
    persist();
    send({ type: 'select', region: id, openSource: tab !== 'graph' });
    render();
  }
  function heading(title, description) {
    return append(
      el('div', 'section-heading'),
      el('h2', '', title),
      description && el('p', 'muted', description)
    );
  }
  function stat(label, value) {
    return append(el('div', 'stat'), el('strong', '', value), el('span', 'muted', label));
  }
  function unexplainedPercent(share) {
    return share > 0 && share < 0.005 ? '<1' : fmt(100 * share);
  }
  function explanationBadge(info) {
    const tag = info.share === null
      ? badge('Unexplained share unavailable', 'warn')
      : badge(`${unexplainedPercent(info.share)}% unexplained${info.estimated ? ' (estimate)' : ''}`,
        info.share > 0.05 ? 'warn' : 'good');
    tag.classList.add('interface-unexplained');
    tag.title = info.reason || (info.estimated
      ? 'Own unexplained work plus full unresolved child terms, divided by interface work. Child costs use measured per-state means and recorded nesting. Fitted child terms do not propagate their internal unexplained work.'
      : 'Unexplained own work divided by the fitted explained and unexplained work.');
    return tag;
  }
  function formulaCard(r, openChild = id => choose(id, 'interface')) {
    const card = el('section', 'card formula-card');
    const childTerms = M.childTerms(model, r.id);
    const formulaWithChildren = (own) => {
      const row = el('div', 'formula', own);
      for (const term of childTerms) {
        row.append(el('span', '', ' + ' + term.prefix));
        const link = button(term.reference, () => openChild(term.child), 'link-button child-interface');
        link.title = 'Open child interface, including its unexplained cost';
        row.append(link, el('span', '', term.suffix));
      }
      return row;
    };
    append(card, el('div', 'eyebrow', 'PERFORMANCE INTERFACE'), el('h1', '', r.name));
    const tags = el('div', 'tags');
    append(
      tags,
      badge('CPU instructions / call'),
      badge(childTerms.length ? 'Own work + direct child interfaces' : 'Own work · nested regions excluded'),
      badge(rawCosts ? 'Marker API cost retained' :
        model.measurement.markerAdjustment?.includes('no wrapper calibration subtraction')
          ? 'Marker modules excluded' : 'Marker adjustment applied')
    );
    if (r.droppedCalls) tags.append(badge(`${r.droppedCalls} calls omitted from fitting`, 'warn'));
    append(card, tags);
    card.append(el('p', 'small muted', 'Costs and percentages rounded to whole numbers for display; calculations retain full precision.'));
    if (childTerms.length)
      card.append(el('p', 'small muted', 'Unexplained includes own unexplained work and the full contribution of unexplained(F[child]) terms. Fitted child terms count as explained here, even when the child has its own unexplained work. Percentages estimate child costs from measured per-state means and recorded calls. Click F to inspect the child. The charts and function breakdown below show own work only.'));
    const statuses = sourceStatuses.get(r.id) || [];
    if (statuses.some((source) => source.state === 'changed'))
      card.append(
        el(
          'p',
          'notice warn',
          'Source differs from the exported snapshot. This is the recorded interface; remeasure edited code before treating it as the current interface.'
        )
      );
    if (statuses.some((source) => source.state === 'unavailable'))
      append(
        card,
        el(
          'p',
          'notice warn',
          'Some source locations are unavailable from the current source root.'
        ),
        button('Configure source root', () => send({ type: 'configureSourceRoot' }), 'quiet')
      );

    if (!r.regimes.length)
      append(
        card,
        childTerms.length ? formulaWithChildren('own (not fitted)') : null,
        childTerms.length ? explanationBadge(M.interfaceExplanation(model, r.id)) : null,
        el(
          'p',
          'empty',
          'There are not enough varied states to fit an interface yet. The measured calls are still available below.'
        )
      );
    for (const fit of r.regimes) {
      const block = el('div', 'regime');
      if (r.regimes.length > 1)
        block.append(
          el(
            'div',
            'muted range-label',
            fit.range.map(([lo, hi], i) => `${lo} ≤ ${r.states[i]} ≤ ${hi}`).join(' · ')
          )
        );
      block.append(formulaWithChildren(M.formula(r, fit)));
      const notes = el('div', 'tags');
      const explanation = M.interfaceExplanation(model, r.id, fit);
      notes.append(explanationBadge(explanation));
      for (const child of explanation.children) {
        if (!child.share) continue;
        const link = button(`unexplained(F[${child.child}]): ${unexplainedPercent(child.share)}%`,
          () => openChild(child.child), 'link-button');
        link.title = 'Contribution to this interface’s unexplained percentage, including the child’s descendants.';
        notes.append(link);
      }
      append(block, notes);
      card.append(block);
    }
    for (const diagnostic of r.diagnostics || []) card.append(el('p', 'notice warn', diagnostic));
    if (
      !rawCosts &&
      (r.diagnostics || []).some((message) => /Marker-overhead|calibrated explained/.test(message))
    )
      card.append(
        button(
          'Inspect recorded counts before marker subtraction',
          () => {
            rawCosts = true;
            model = M.recordedCosts(loadedModel);
            render();
          },
          'secondary'
        )
      );
    const stats = el('div', 'stats');
    append(
      stats,
      stat(r.droppedCalls ? 'retained calls' : 'recorded calls', fmt(r.calls)),
      stat('observed states', fmt(r.points.length)),
      stat('declared PCVs', r.states.length)
    );
    card.append(stats);
    const sources = el('div', 'source-links');
    r.sources.forEach((source, i) =>
      sources.append(
        button(
          `${source.path}:${source.line} ↗`,
          () => send({ type: 'source', region: r.id, index: i }),
          'link-button'
        )
      )
    );
    if (!r.sources.length)
      sources.append(el('span', 'muted', 'No source mapping · export with --source-root'));
    if (r.sources.length > 1)
      sources.append(
        el(
          'span',
          'muted',
          'Multiple annotations share this region name; measurements are aggregated.'
        )
      );
    card.append(sources);
    return card;
  }
  function svg(tag, attributes = {}, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function observations(r) {
    const card = append(
      el('section', 'card'),
      heading(
        'What the run observed',
        'Own explained and unexplained work at the measured states; child terms are excluded from this chart. No claim between these points.'
      )
    );
    const points = r.regimes.length
      ? r.regimes.flatMap((fit) => fit.points)
      : r.points.map((p) => ({ ...p, explained: 0, unexplained: p.observed }));
    if (!points.length) {
      card.append(el('p', 'muted', 'No retained state points.'));
      return card;
    }
    const sampled =
      points.length <= 60
        ? points
        : points.filter((_, i) => i % Math.ceil(points.length / 60) === 0);
    const width = 760,
      height = 230,
      left = 62,
      right = 20,
      bottom = 40,
      top = 18;
    const max = Math.max(1, ...sampled.map((p) => Math.max(0, p.explained) + p.unexplained));
    const chart = svg('svg', {
      viewBox: `0 0 ${width} ${height}`,
      role: 'img',
      'aria-label': 'Observed explained and unexplained instruction costs',
      class: 'observations-chart'
    });
    for (let i = 0; i <= 4; ++i) {
      const y = height - bottom - (i * (height - top - bottom)) / 4;
      chart.append(svg('line', { x1: left, y1: y, x2: width - right, y2: y, class: 'grid-line' }));
      chart.append(
        svg(
          'text',
          { x: left - 9, y: y + 4, 'text-anchor': 'end', class: 'chart-label' },
          compact((max * i) / 4)
        )
      );
    }
    const step = (width - left - right) / sampled.length,
      scale = (height - top - bottom) / max;
    sampled.forEach((point, i) => {
      const x = left + step * i + Math.min(4, step / 5),
        w = Math.max(1, step - Math.min(8, step / 3));
      const explained = Math.max(0, point.explained),
        y = height - bottom - explained * scale;
      const group = svg('g', { tabindex: 0 });
      group.append(
        svg(
          'title',
          {},
          `${stateLabel(r.states, point.state)}\nExplained: ${fmt(point.explained)}\nUnexplained: ${fmt(point.unexplained)}\nCalls: ${point.calls}`
        )
      );
      group.append(
        svg('rect', { x, y, width: w, height: explained * scale, class: 'bar-explained', rx: 2 })
      );
      group.append(
        svg('rect', {
          x,
          y: y - point.unexplained * scale,
          width: w,
          height: point.unexplained * scale,
          class: 'bar-unexplained',
          rx: 2
        })
      );
      if (sampled.length <= 12 || i % Math.ceil(sampled.length / 8) === 0)
        group.append(
          svg(
            'text',
            { x: x + w / 2, y: height - 17, 'text-anchor': 'middle', class: 'chart-label' },
            point.state.length === 1 ? String(point.state[0]) : String(i + 1)
          )
        );
      chart.append(group);
    });
    card.append(chart);
    append(
      card,
      append(
        el('div', 'legend'),
        el('span', 'legend-explained', 'Explained'),
        el('span', 'legend-unexplained', r.regimes.length ? 'Unexplained' : 'Not fitted'),
        el('span', 'muted', r.states.length === 1 ? r.states[0] : 'State combinations')
      )
    );
    if (points.length > sampled.length)
      card.append(
        el(
          'p',
          'muted small',
          `Showing ${sampled.length} of ${points.length} state points. The table retains all points.`
        )
      );
    const details = el('details');
    details.append(el('summary', '', `Inspect ${points.length} observed states`));
    const table = el('table');
    table.append(
      append(
        el('thead'),
        append(
          el('tr'),
          ...['PCVs', 'Calls', 'Explained', 'Unexplained'].map((h) => el('th', '', h))
        )
      )
    );
    const body = el('tbody'),
      controls = el('div', 'actions');
    let pageIndex = 0;
    const pageSize = 200;
    const drawPage = () => {
      body.replaceChildren();
      controls.replaceChildren();
      const start = pageIndex * pageSize;
      for (const p of points.slice(start, start + pageSize))
        body.append(
          append(
            el('tr'),
            el('td', 'mono', stateLabel(r.states, p.state)),
            el('td', 'number', fmt(p.calls)),
            el('td', 'number', fmt(p.explained)),
            el('td', 'number', fmt(p.unexplained))
          )
        );
      controls.append(
        el(
          'span',
          'small muted',
          `${start + 1}–${Math.min(start + pageSize, points.length)} of ${points.length} states`
        )
      );
      if (pageIndex > 0)
        controls.append(
          button(
            'Previous states',
            () => {
              --pageIndex;
              drawPage();
            },
            'quiet'
          )
        );
      if (start + pageSize < points.length)
        controls.append(
          button(
            'Next states',
            () => {
              ++pageIndex;
              drawPage();
            },
            'quiet'
          )
        );
    };
    details.addEventListener('toggle', () => {
      if (details.open && !body.children.length) drawPage();
    });
    append(table, body);
    append(details, controls, append(el('div', 'table-scroll'), table));
    card.append(details);
    return card;
  }
  function compact(value) {
    if (value >= 1e9) return fmt(value / 1e9) + 'G';
    if (value >= 1e6) return fmt(value / 1e6) + 'M';
    if (value >= 1e3) return fmt(value / 1e3) + 'k';
    return fmt(value);
  }
  function attribution(r) {
    const card = append(
      el('section', 'card'),
      heading(
        'Where the cost comes from',
        'Functions contributing to this region’s own explained and unexplained work. Child terms are shown in the interface above.'
      )
    );
    if (!r.regimes.length) {
      card.append(el('p', 'muted', 'Attribution will appear after enough states are measured.'));
      return card;
    }
    r.regimes.forEach((fit, i) => {
      if (r.regimes.length > 1) card.append(el('h3', '', `Regime ${i + 1}`));
      const groups = [
        ...r.states.map((state, j) => [state + ' coefficient', fit.attribution.coefficients[j]]),
        ['Constant', fit.attribution.constant],
        ['Unexplained', fit.attribution.unexplained]
      ];
      for (const [label, functions] of groups) {
        if (!functions.length) continue;
        const details = el('details');
        details.open = label === 'Unexplained' && fit.unexplainedShare > 0.05;
        details.append(el('summary', '', label));
        const list = el('ul', 'function-list');
        for (const fn of functions)
          list.append(
            append(
              el('li'),
              append(el('div'), el('code', '', fn.function), el('small', 'muted', fn.module)),
              el('span', 'number', fmt(fn.instructions))
            )
          );
        append(details, list);
        card.append(details);
      }
    });
    return card;
  }
  function interfaceView(r) {
    const main = el('div', 'interface-view');
    append(main, formulaCard(r), observations(r));
    if (model.composition?.status !== 'observed' && Object.keys(r.nested || {}).length) {
      const nested = append(
        el('section', 'card'),
        heading(
          'Nested marked calls',
          'These measured calls are excluded from this region’s own instruction formula. Counts are means per parent call and include descendants at any depth; they are not a cost total.'
        )
      );
      const list = el('ul', 'function-list');
      for (const [name, count] of Object.entries(r.nested).sort((a, b) => b[1] - a[1])) {
        const target = model.regions.find((r) => r.id === name);
        list.append(
          append(
            el('li'),
            target
              ? button(target.name, () => choose(name), 'link-button')
              : el('span', 'mono', name),
            el('span', 'number', fmt(count) + ' calls')
          )
        );
      }
      nested.append(list);
      main.append(nested);
    }
    const related = model.relations.filter(
      (relation) =>
        relation.target.region === r.id || relation.terms.some((term) => term.region === r.id)
    );
    const relations = append(
      el('section', 'card'),
      heading('Connected state', `${related.length} observed relationships touch this region.`)
    );
    related.slice(0, 4).forEach((relation) =>
      relations.append(
        button(
          M.relationship(relation),
          () => {
            activeTab = 'relations';
            render();
          },
          'relation-preview'
        )
      )
    );
    relations.append(
      button(
        'Explore all relationships →',
        () => {
          activeTab = 'relations';
          render();
        },
        'link-button'
      )
    );
    const next = append(el('section', 'card'), heading('Next small experiment'));
    const list = el('ul', 'suggestions');
    M.suggestedExperiments(model, r).forEach((text) => list.append(el('li', '', text)));
    append(
      next,
      list,
      button(
        'Try a PCV scenario →',
        () => {
          activeTab = 'scenario';
          ensureEdit(r);
          render();
        },
        'secondary'
      )
    );
    append(main, append(el('div', 'two-columns'), relations, next), attribution(r));
    return main;
  }
  function connectionGraph() {
    const card = append(
      el('section', 'card'),
      heading(
        'Observed connections',
        'Arrows show equation dependencies in the recorded trace. They do not establish causality.'
      )
    );
    const all = M.graph(model);
    const connected = [
      ...new Set(all.edges.flatMap((e) => [JSON.parse(e.source)[0], JSON.parse(e.target)[0]]))
    ];
    const focus = connected.includes(selected) ? [selected] : [];
    for (let index = 0; index < focus.length && focus.length < 16; ++index) {
      const current = focus[index];
      for (const edge of all.edges) {
        const from = JSON.parse(edge.source)[0],
          to = JSON.parse(edge.target)[0];
        const other = from === current ? to : to === current ? from : null;
        if (other !== null && !focus.includes(other)) focus.push(other);
        if (focus.length >= 16) break;
      }
    }
    const names = [...focus, ...connected.filter((name) => !focus.includes(name))].slice(0, 16);
    if (!names.length) {
      card.append(
        el('p', 'muted', 'No cross-region relationship was found within the discovery budget.')
      );
      return card;
    }
    const edges = all.edges.filter(
      (e) => names.includes(JSON.parse(e.source)[0]) && names.includes(JSON.parse(e.target)[0])
    );
    const level = new Map(names.map((n) => [n, 0]));
    // Bound relaxation: cycles remain visible but never stall the layout.
    for (let i = 0; i < Math.min(names.length, 5); ++i)
      for (const edge of edges) {
        const from = JSON.parse(edge.source)[0],
          to = JSON.parse(edge.target)[0];
        if (from !== to) level.set(to, Math.min(4, Math.max(level.get(to), level.get(from) + 1)));
      }
    const columns = new Map();
    for (const name of names) {
      const column = level.get(name);
      if (!columns.has(column)) columns.set(column, []);
      columns.get(column).push(name);
    }
    const w = (Math.max(...columns.keys()) + 1) * 170 + 20,
      h = Math.max(160, ...[...columns.values()].map((c) => c.length * 84 + 40));
    const chart = svg('svg', {
      viewBox: `0 0 ${w} ${h}`,
      class: 'connection-graph',
      role: 'img',
      'aria-label': 'Relationships among measured regions'
    });
    const defs = svg('defs'),
      marker = svg('marker', {
        id: 'arrow',
        viewBox: '0 0 10 10',
        refX: 9,
        refY: 5,
        markerWidth: 5,
        markerHeight: 5,
        orient: 'auto-start-reverse'
      });
    marker.append(svg('path', { d: 'M 0 0 L 10 5 L 0 10 z', class: 'edge-arrow' }));
    defs.append(marker);
    chart.append(defs);
    const positions = new Map();
    for (const [column, members] of columns)
      members.forEach((name, row) =>
        positions.set(name, { x: column * 170 + 12, y: 25 + row * 84 })
      );
    const unique = new Set();
    for (const edge of edges) {
      const from = JSON.parse(edge.source)[0],
        to = JSON.parse(edge.target)[0],
        key = from + '\0' + to;
      if (unique.has(key)) continue;
      unique.add(key);
      const a = positions.get(from),
        b = positions.get(to);
      const d =
        from === to
          ? `M ${a.x + 20} ${a.y} C ${a.x + 10} ${a.y - 28}, ${a.x + 95} ${a.y - 28}, ${a.x + 90} ${a.y}`
          : `M ${a.x + 128} ${a.y + 23} C ${a.x + 155} ${a.y + 23}, ${b.x - 28} ${b.y + 23}, ${b.x} ${b.y + 23}`;
      const line = svg('path', {
        d,
        class: 'graph-edge' + (from === selected || to === selected ? ' highlighted' : ''),
        'marker-end': 'url(#arrow)'
      });
      line.append(svg('title', {}, `${from} → ${to} (${edge.kind})`));
      chart.append(line);
    }
    for (const [name, pos] of positions) {
      const node = svg('g', {
        class: 'graph-node' + (name === selected ? ' selected' : ''),
        tabindex: 0,
        role: 'button',
        'aria-label': 'Inspect ' + name
      });
      node.append(svg('rect', { x: pos.x, y: pos.y, width: 128, height: 46, rx: 8 }));
      node.append(
        svg(
          'text',
          { x: pos.x + 64, y: pos.y + 28, 'text-anchor': 'middle' },
          name.length > 16 ? name.slice(0, 15) + '…' : name
        )
      );
      node.addEventListener('click', () => choose(name));
      node.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') choose(name);
      });
      chart.append(node);
    }
    card.append(chart);
    if (connected.length > names.length)
      card.append(
        el(
          'p',
          'muted small',
          `Graph shows ${names.length} of ${connected.length} connected regions, prioritizing the selected region’s neighborhood. The list below includes every discovered relationship.`
        )
      );
    return card;
  }
  function relationshipsView() {
    const main = el('div');
    append(main, relationshipCheckView(), connectionGraph());
    const card = append(
      el('section', 'card'),
      heading(
        'All discovered relationships',
        `${model.relations.length} equalities held at their recorded target calls. Alternative equations can disagree after an intervention.`
      )
    );
    if (model.discovery?.truncated || model.discovery?.warnings?.length)
      card.append(
        el(
          'div',
          'notice warn',
          'Discovery was limited. ' + (model.discovery.warnings || []).join(' ')
        )
      );
    const search = el('input', 'search');
    search.type = 'search';
    search.placeholder = 'Filter by region, PCV, or history operation';
    search.setAttribute('aria-label', 'Filter relationships');
    const list = el('div', 'relationship-list');
    const draw = () => {
      list.replaceChildren();
      const matches = model.relations.filter((r) =>
        M.relationship(r).toLowerCase().includes(search.value.toLowerCase())
      );
      for (const relation of matches) {
        const row = el('article', 'relationship');
        append(
          row,
          el('code', 'equation', M.relationship(relation)),
          append(
            el('div', 'tags'),
            badge('observed · exact at sampled calls', 'observed'),
            el(
              'span',
              'muted small',
              `${relation.evidence?.calls ?? '?'} calls · ${relation.evidence?.groups ?? '?'} process/run groups`
            )
          )
        );
        const alternatives = relation.terms.reduce((n, t) => n + (t.aliases?.length || 0), 0);
        if (alternatives)
          row.append(
            el(
              'p',
              'muted small',
              `${alternatives} history features coincide with these terms in this trace. That equivalence is not guaranteed after a change.`
            )
          );
        append(
          row,
          button(
            'Inspect ' + relation.target.region,
            () => choose(relation.target.region, 'interface'),
            'link-button'
          )
        );
        list.append(row);
      }
      if (!matches.length) list.append(el('p', 'empty', 'No matching relationships.'));
    };
    search.addEventListener('input', draw);
    draw();
    append(card, search, list);
    main.append(card);
    return main;
  }
  function select(options, value, label, onChange) {
    const element = el('select');
    element.setAttribute('aria-label', label);
    options.forEach(([key, text]) => {
      const option = el('option', '', text);
      option.value = key;
      element.append(option);
    });
    element.value = value;
    element.addEventListener('change', () => onChange(element.value));
    return element;
  }
  function ensureEdit(r = region()) {
    if (!edits.length && r?.states.length)
      edits.push({ region: r.id, state: r.states[0], op: 'scale', value: 2 });
    if (!edits.length) {
      const first = model.regions.find((r) => r.states.length);
      if (first) edits.push({ region: first.id, state: first.states[0], op: 'scale', value: 2 });
    }
  }
  function currentScenario() {
    return {
      edits: structuredClone(edits),
      relations: [...assumptionIds],
      proposals: structuredClone(proposals),
      costBasis: rawCosts ? 'recorded' : 'calibrated',
      auditAlternatives
    };
  }
  async function updateScenario() {
    persist();
    const scenario = currentScenario();
    const key = JSON.stringify(scenario);
    const paint = () => {
      const target = document.getElementById('scenario-result');
      if (target) target.replaceChildren(scenarioResults());
    };
    if (
      scenarioCache?.model === model &&
      scenarioCache.measured === validationModel &&
      scenarioCache.key === key
    ) {
      paint();
      return;
    }
    scenarioCache = { model, measured: validationModel, key };
    const generation = ++scenarioGeneration;
    scenarioPending = true;
    result = null;
    scenarioError = '';
    scenarioValidation = null;
    scenarioValidationError = '';
    paint();
    try {
      const response = await analysis.request('scenario', model, {
        scenario,
        measured: validationModel
      });
      if (generation !== scenarioGeneration) return;
      result = response.result;
      scenarioValidation = response.validation;
      scenarioValidationError = response.validationError || '';
      send({
        type: 'analysisFinished',
        baseModelId: loadedModel.id,
        modelId: result.modelId,
        backend: analysis.backend,
        validationStructureMatches: scenarioValidation?.structureMatches,
        validationMeasuredId: scenarioValidation?.measuredModelId,
        changedRegions: result.regions.filter((r) => r.changedCalls).map((r) => r.region)
      });
    } catch (error) {
      if (generation !== scenarioGeneration) return;
      scenarioError = error.message;
      send({
        type: 'analysisFinished',
        baseModelId: loadedModel.id,
        error: error.message,
        backend: analysis.backend
      });
    } finally {
      if (generation === scenarioGeneration) {
        scenarioPending = false;
        paint();
      }
    }
  }
  function scenarioResults() {
    const main = el('div');
    if (scenarioPending) {
      main.append(el('p', 'analysis-pending', 'Checking the scenario…'));
      return main;
    }
    if (scenarioError) {
      main.append(el('div', 'notice warn', scenarioError));
      return main;
    }
    if (!result) return main;
    result.warnings.forEach((message) => main.append(el('p', 'scenario-note', message)));
    const card = append(
      el('section', 'card'),
      heading(
        'Changes by region',
        'Mean explained instructions per call. Rows are independent; they are not added into total cost or latency.'
      )
    );
    const label = el('label', 'check-label'),
      checkbox = el('input');
    checkbox.type = 'checkbox';
    checkbox.checked = onlyAffected;
    checkbox.addEventListener('change', () => {
      onlyAffected = checkbox.checked;
      updateScenario();
    });
    append(label, checkbox, el('span', '', 'Only regions with changed PCVs'));
    card.append(label);
    const table = el('table', 'scenario-table');
    table.append(
      append(
        el('thead'),
        append(
          el('tr'),
          ...['Region', 'Before', 'Scenario', 'Change', 'Support'].map((h) => el('th', '', h))
        )
      )
    );
    const body = el('tbody');
    const rows = result.regions
      .filter((row) => !onlyAffected || row.changedCalls)
      .sort((a, b) => Math.abs(b.delta || 0) - Math.abs(a.delta || 0));
    for (const row of rows) {
      const tr = el('tr');
      tr.dataset.region = row.region;
      const name = append(
        el('td'),
        button(row.region, () => choose(row.region, 'interface'), 'link-button'),
        el('small', 'muted', `${row.changedCalls}/${row.calls} calls have changed PCVs`)
      );
      const delta = row.delta === null ? 'Unknown' : (row.delta > 0 ? '+' : '') + fmt(row.delta);
      const support = el('td', 'support');
      row.support.forEach((value) =>
        support.append(badge(value, value === 'observed' ? 'observed' : 'warn'))
      );
      if (row.unknownCalls)
        support.append(badge(`${row.modelledCalls}/${row.calls} calls modelled`, 'warn'));
      if (row.unobservedBaselineCalls)
        support.append(badge(`${row.unobservedBaselineCalls} baseline states not in fit`, 'warn'));
      if (row.unexplainedCalls) support.append(badge('Unexplained cost not predicted', 'warn'));
      row.reasons.forEach((reason) => support.append(el('small', 'muted', reason)));
      append(
        tr,
        name,
        el('td', 'number', row.before === null ? '—' : fmt(row.before)),
        el('td', 'number', row.after === null ? '—' : fmt(row.after)),
        el('td', 'number ' + (row.delta > 0 ? 'increase' : row.delta < 0 ? 'decrease' : ''), delta),
        support
      );
      body.append(tr);
    }
    table.append(body);
    card.append(append(el('div', 'table-scroll'), table));
    if (!rows.length)
      card.append(
        el(
          'p',
          'empty',
          'No recorded PCVs changed. Choose an intervention or enable relationships as assumptions.'
        )
      );
    append(
      card,
      append(
        el('div', 'actions'),
        button(
          'Save scenario and per-region results',
          () => send({ type: 'exportScenario', scenario: result.scenario }),
          'secondary'
        ),
        button(
          'Compare against a new measured report',
          () => send({ type: 'loadValidationReport' }),
          'secondary'
        )
      )
    );
    main.append(card);
    if (result.alternativeChecks) {
      const disagreements = result.alternativeChecks.filter((row) => row.disagreements);
      const audit = append(
        el('section', 'card'),
        heading(
          'Which relationships need another experiment?',
          `${result.alternativeChecks.length} alternative equations checked in the selected scenario history. These are predictions, not measured counterexamples.`
        )
      );
      if (!disagreements.length)
        audit.append(
          el(
            'p',
            'muted',
            'No disagreements found for these interventions. Agreement does not establish causality.'
          )
        );
      for (const row of disagreements) {
        const detail = el('details', 'relationship');
        detail.open = disagreements.length <= 3;
        detail.append(
          el(
            'summary',
            '',
            `${row.target.region}.${row.target.state}: disagreement at ${row.disagreements}/${row.calls} calls`
          )
        );
        append(
          detail,
          el('code', 'equation', 'Selected: ' + row.selectedEquation),
          el('code', 'equation', 'Alternative: ' + row.candidateEquation)
        );
        for (const example of row.examples)
          detail.append(
            el(
              'p',
              'mono small',
              `call ${example.seq}: selected ${example.selectedValue}, alternative ${example.alternativeValue}`
            )
          );
        detail.append(
          el(
            'p',
            'small muted',
            'If this intervention can be realized in the program, a small new run can distinguish these equations.'
          )
        );
        audit.append(detail);
      }
      main.append(audit);
    }
    if (validationModel) main.append(validationView());
    const detail = el('details', 'card');
    detail.append(el('summary', '', 'Inspect propagated state changes'));
    for (const row of rows) {
      if (!row.changes.length) continue;
      detail.append(el('h3', '', row.region));
      for (const change of row.changes) {
        const call = el('details', 'change-explanation');
        call.append(
          el(
            'summary',
            '',
            `call ${change.seq}: ${JSON.stringify(change.before)} → ${JSON.stringify(change.after)}`
          )
        );
        for (const step of change.derivations || []) {
          if (step.equation) {
            call.append(el('code', 'equation', step.equation));
            for (const input of step.inputs)
              call.append(
                el(
                  'div',
                  'mono small',
                  `${input.kind}(${input.region}${input.state === null ? '' : '.' + input.state}) = ${input.value}`
                )
              );
            call.append(el('p', 'small', `Computed ${step.state} = ${step.result}`));
          } else
            call.append(
              el(
                'p',
                'small',
                `Direct ${step.intervention} intervention on ${step.state}: ${step.before} → ${step.result}`
              )
            );
        }
        detail.append(call);
      }
    }
    main.append(detail);
    return main;
  }
  function validationView() {
    const card = append(
      el('section', 'card'),
      heading(
        'Check against a new execution',
        validationName + ' · State propagation and cost prediction are checked separately.'
      )
    );
    const validation = scenarioValidation;
    if (scenarioValidationError) {
      card.append(el('p', 'notice warn', scenarioValidationError));
      return card;
    }
    if (!validation) {
      card.append(el('p', 'muted', 'Checking the new execution…'));
      return card;
    }
    if (!validation.structureMatches) {
      card.append(el('p', 'notice warn', validation.reason));
      return card;
    }
    card.append(
      el(
        'p',
        'small muted',
        'Calls, marker order, thread roles, and nesting match. Cost error uses only predictions with no unexplained blocks and compares against measured per-state means.'
      )
    );
    const table = el('table');
    table.append(
      append(
        el('thead'),
        append(
          el('tr'),
          ...[
            'Region',
            'State matches',
            'Cost checks',
            'Predicted',
            'Measured',
            'Absolute error'
          ].map((h) => el('th', '', h))
        )
      )
    );
    const body = el('tbody');
    for (const row of validation.regions) {
      const error =
        row.relativeAbsoluteError === null
          ? 'Not checked'
          : fmt(100 * row.relativeAbsoluteError) + '%';
      const tr = el('tr');
      tr.dataset.validationRegion = row.region;
      append(
        tr,
        append(
          el('td'),
          button(row.region, () => choose(row.region, 'interface'), 'link-button')
        ),
        el('td', 'number', `${row.stateMatches}/${row.calls}`),
        el('td', 'number', `${row.costChecks}/${row.calls}`),
        el('td', 'number', row.meanPredicted === null ? '—' : fmt(row.meanPredicted)),
        el('td', 'number', row.meanObserved === null ? '—' : fmt(row.meanObserved)),
        el('td', 'number ' + (row.relativeAbsoluteError > 0.05 ? 'increase' : ''), error)
      );
      body.append(tr);
      if (row.examples.length) {
        const examples = el('tr'),
          cell = el('td');
        cell.colSpan = 6;
        const detail = el('details');
        detail.append(el('summary', '', 'Inspect disagreements'));
        row.examples.forEach((example) =>
          detail.append(el('pre', 'state-change', JSON.stringify(example, null, 2)))
        );
        cell.append(detail);
        examples.append(cell);
        body.append(examples);
      }
    }
    table.append(body);
    card.append(append(el('div', 'table-scroll'), table));
    card.append(
      button(
        'Clear validation report',
        () => {
          validationModel = null;
          updateScenario();
        },
        'quiet'
      )
    );
    return card;
  }
  function proposalView() {
    const card = append(
      el('section', 'card'),
      heading(
        'Propose a state relationship',
        'State relationships may be nonlinear or conditional; each region’s cost interface stays affine in its declared PCVs. The expression is checked against every recorded target call.'
      )
    );
    const targets = model.regions.filter((r) => r.states.length);
    if (!targets.length) return card;
    if (!proposalDraft) {
      const r = region().states.length ? region() : targets[0];
      proposalDraft = { target: { region: r.id, state: r.states[0] }, expression: '' };
    }
    const row = el('div', 'actions');
    append(
      row,
      select(
        targets.map((r) => [r.id, r.name]),
        proposalDraft.target.region,
        'Proposed target region',
        (value) => {
          proposalDraft.target = {
            region: value,
            state: model.regions.find((r) => r.id === value).states[0]
          };
          proposalResult = null;
          render();
        }
      ),
      select(
        model.regions.find((r) => r.id === proposalDraft.target.region).states.map((s) => [s, s]),
        proposalDraft.target.state,
        'Proposed target PCV',
        (value) => {
          proposalDraft.target.state = value;
          proposalResult = null;
        }
      )
    );
    const input = el('input', 'search mono');
    input.setAttribute('aria-label', 'Proposed state expression');
    input.placeholder = 'last("dequeue", "items") ** 2';
    input.value = proposalDraft.expression;
    input.addEventListener('input', () => {
      proposalDraft.expression = input.value;
      proposalResult = null;
    });
    append(
      card,
      row,
      input,
      el(
        'p',
        'small muted',
        'History: last("region", "pcv"), cum(...), cumend(...), count("region"). Integer arithmetic: + − * // % **. Branches: condition ? then : else. Histories before the current call are used.'
      ),
      button(
        'Check proposed relationship',
        async () => {
          const currentModel = model,
            draft = structuredClone(proposalDraft),
            key = JSON.stringify(draft);
          proposalResult = { pending: true };
          render();
          let checked;
          try {
            checked = await analysis.request('proposal', currentModel, draft);
          } catch (error) {
            checked = { error: error.message };
          }
          if (model !== currentModel || JSON.stringify(proposalDraft) !== key) return;
          proposalResult = checked;
          if (activeTab === 'scenario') render();
        },
        'secondary'
      )
    );
    if (proposalResult?.pending)
      card.append(el('p', 'analysis-pending', 'Checking recorded target calls…'));
    else if (proposalResult?.error) card.append(el('p', 'notice warn', proposalResult.error));
    else if (proposalResult) {
      const { relation, check } = proposalResult;
      card.append(
        el(
          'p',
          'notice ' + (check.holds ? '' : 'warn'),
          check.holds
            ? `Matches all ${check.calls} recorded target calls. This is evidence on this trace, not a proof for new inputs.`
            : `Failed at ${check.mismatches} of ${check.calls} recorded target calls.`
        )
      );
      for (const example of check.examples)
        card.append(el('pre', 'state-change', JSON.stringify(example, null, 2)));
      if (check.holds)
        card.append(
          button(
            'Use checked proposal as an assumption',
            () => {
              const available = scenarioModel().relations;
              assumptionIds = assumptionIds.filter(
                (id) =>
                  !available.some(
                    (r) =>
                      r.id === id &&
                      r.target.region === relation.target.region &&
                      r.target.state === relation.target.state
                  )
              );
              proposals = proposals.filter(
                (p) =>
                  M.id(p.target.region, p.target.state) !==
                  M.id(relation.target.region, relation.target.state)
              );
              proposals.push({ target: relation.target, expression: relation.expression });
              assumptionIds.push(relation.id);
              proposalResult = null;
              render();
            },
            'secondary'
          )
        );
    }
    if (proposals.length)
      card.append(
        button(
          'Remove proposed relationships',
          () => {
            const ids = new Set(
              scenarioModel()
                .relations.filter((r) => r.proposed)
                .map((r) => r.id)
            );
            assumptionIds = assumptionIds.filter((id) => !ids.has(id));
            proposals = [];
            proposalResult = null;
            render();
          },
          'quiet'
        )
      );
    return card;
  }
  function scenarioView() {
    if (model.validity?.errors?.length || model.validity?.traceErrors?.length)
      return el('p', 'empty', 'Correct the measurement errors before running scenarios.');
    ensureEdit();
    const main = el('div');
    const card = append(
      el('section', 'card'),
      heading(
        'What if a PCV changed?',
        'Change one or more declared states, then choose which observed relationships to use as assumptions.'
      )
    );
    const editing = el('div', 'interventions');
    edits.forEach((edit, index) => {
      const row = el('div', 'intervention');
      append(
        row,
        select(
          model.regions.filter((r) => r.states.length).map((r) => [r.id, r.name]),
          edit.region,
          'Region for intervention ' + (index + 1),
          (value) => {
            edit.region = value;
            edit.state = model.regions.find((r) => r.id === value).states[0];
            render();
          }
        ),
        select(
          model.regions.find((r) => r.id === edit.region).states.map((s) => [s, s]),
          edit.state,
          'PCV for intervention ' + (index + 1),
          (value) => {
            edit.state = value;
            updateScenario();
          }
        ),
        select(
          [
            ['scale', 'multiply by'],
            ['add', 'add'],
            ['set', 'set to']
          ],
          edit.op,
          'Operation ' + (index + 1),
          (value) => {
            edit.op = value;
            updateScenario();
          }
        )
      );
      const input = el('input', 'value-input');
      input.type = 'number';
      input.step = 'any';
      input.value = String(edit.value);
      input.setAttribute('aria-label', 'Intervention value ' + (index + 1));
      input.addEventListener('input', () => {
        edit.value = input.value === '' ? NaN : Number(input.value);
        updateScenario();
      });
      append(
        row,
        input,
        button(
          'Remove',
          () => {
            edits.splice(index, 1);
            render();
          },
          'quiet'
        )
      );
      editing.append(row);
    });
    append(
      card,
      editing,
      button(
        '+ Add another PCV',
        () => {
          const r = region().states.length ? region() : model.regions.find((r) => r.states.length);
          if (r) edits.push({ region: r.id, state: r.states[0], op: 'scale', value: 2 });
          render();
        },
        'secondary'
      )
    );
    main.append(card);
    const results = el('div');
    results.id = 'scenario-result';
    main.append(results);
    const availableRelations = scenarioModel().relations;
    const assumptions = append(
      el('section', 'card'),
      heading(
        'Relationship assumptions',
        `${assumptionIds.length} selected. Nothing propagates through an observed equation until you opt in.`
      )
    );
    const auditLabel = el('label', 'check-label'),
      audit = el('input');
    audit.type = 'checkbox';
    audit.checked = auditAlternatives;
    audit.addEventListener('change', () => {
      auditAlternatives = audit.checked;
      updateScenario();
    });
    append(auditLabel, audit, el('span', '', 'Compare alternative relationships'));
    assumptions.append(auditLabel);
    const actions = el('div', 'actions');
    append(
      actions,
      button(
        'Use first observed equation for each target',
        () => {
          const unique = new Map();
          for (const r of availableRelations) {
            const key = M.id(r.target.region, r.target.state);
            if (!unique.has(key)) unique.set(key, r.id);
          }
          assumptionIds = [...unique.values()];
          render();
        },
        'secondary'
      ),
      button(
        'Clear assumptions',
        () => {
          assumptionIds = [];
          render();
        },
        'quiet'
      )
    );
    assumptions.append(actions);
    const targets = new Map();
    for (const relation of availableRelations) {
      const key = M.id(relation.target.region, relation.target.state);
      if (!targets.has(key)) targets.set(key, []);
      targets.get(key).push(relation);
    }
    const details = el('details');
    details.open = targets.size <= 8;
    details.append(el('summary', '', `Choose equations for ${targets.size} target states`));
    for (const choices of targets.values()) {
      const target = choices[0].target;
      const row = el('label', 'assumption-row');
      append(
        row,
        el('span', 'mono', target.region + '.' + target.state),
        select(
          [['', 'No propagation'], ...choices.map((r) => [r.id, M.relationship(r)])],
          choices.find((r) => assumptionIds.includes(r.id))?.id || '',
          `Relationship for ${target.region}.${target.state}`,
          (value) => {
            const ids = new Set(choices.map((r) => r.id));
            assumptionIds = assumptionIds.filter((id) => !ids.has(id));
            if (value) assumptionIds.push(value);
            render();
          }
        )
      );
      details.append(row);
    }
    assumptions.append(details);
    main.append(assumptions);
    main.append(proposalView());
    main.append(experimentView());
    // Update after insertion by render().
    return main;
  }
  function experimentView() {
    const card = append(
      el('section', 'card'),
      heading(
        'Choose the next small experiment',
        'Search for a single PCV change that separates observed explanations. Uses your chosen relationships from the recorded baseline; current interventions are not included.'
      )
    );
    const assumptions = {
      relations: [...assumptionIds],
      proposals: structuredClone(proposals),
      costBasis: rawCosts ? 'recorded' : 'calibrated'
    };
    const key = JSON.stringify(assumptions);
    const current =
      experimentCache?.model === model && experimentCache.key === key ? experimentCache : null;
    const action = button(
      current?.pending ? 'Searching…' : 'Find distinguishing experiments',
      () => {
        const cache = (experimentCache = { model, key, pending: true });
        render();
        analysis
          .request('experiments', model, { assumptions })
          .then((value) => {
            cache.value = value;
          })
          .catch((error) => {
            cache.error = error.message;
          })
          .finally(() => {
            cache.pending = false;
            if (experimentCache === cache && activeTab === 'scenario') render();
          });
      },
      'secondary'
    );
    action.disabled = !assumptionIds.length || !!current?.pending;
    card.append(action);
    if (!assumptionIds.length)
      card.append(el('p', 'small muted', 'Select at least one relationship assumption first.'));
    if (current?.error) card.append(el('p', 'notice warn', current.error));
    if (current?.value) {
      const value = current.value;
      card.append(
        el(
          'p',
          'small muted',
          `${value.search.tried}/${value.search.possibleProbes} candidate probes checked; ${value.search.ambiguousTargets} targets have competing observed equations. ${value.search.truncated ? 'Search was bounded, not exhaustive.' : ''}`
        )
      );
      card.append(
        el(
          'p',
          'notice warn',
          'These are conditional PCV experiments, not generated program inputs. Check that each change can be implemented while retaining the recorded call structure, then measure a small run.'
        )
      );
      if (!value.suggestions.length)
        card.append(
          el(
            'p',
            'muted',
            'No distinguishing experiment found within this search. Agreement is not proof of causality.'
          )
        );
      for (const suggestion of value.suggestions) {
        const item = el('details', 'experiment-suggestion');
        const edit = suggestion.edit;
        item.dataset.experimentRegion = edit.region;
        item.dataset.experimentState = edit.state;
        item.dataset.experimentOp = edit.op;
        item.append(
          el(
            'summary',
            '',
            `${edit.region}.${edit.state}: ${edit.op === 'add' ? 'add 1' : 'multiply by 2'} · separates ${suggestion.targets.length} target PCVs`
          )
        );
        item.append(
          el(
            'p',
            'small',
            'Measure: ' + suggestion.targets.map((t) => t.region + '.' + t.state).join(', ')
          )
        );
        for (const check of suggestion.disagreements) {
          item.append(
            el(
              'p',
              'small',
              `${check.target.region}.${check.target.state}: ${check.disagreements}/${check.calls} calls disagree`
            )
          );
          append(
            item,
            el('code', 'equation', check.selectedEquation),
            el('code', 'equation', check.candidateEquation)
          );
        }
        item.append(
          button(
            'Replace interventions with this probe',
            () => {
              edits = structuredClone(suggestion.scenario.edits);
              auditAlternatives = true;
              render();
            },
            'secondary'
          )
        );
        card.append(item);
      }
      if (value.rejected.length) {
        const failures = el('details');
        failures.append(
          el(
            'summary',
            '',
            `${value.rejected.length} probes could not be replayed under the selected assumptions`
          )
        );
        for (const failure of value.rejected)
          failures.append(
            el(
              'p',
              'small',
              `${failure.edit.region}.${failure.edit.state} ${failure.edit.op} ${failure.edit.value}: ${failure.reason}`
            )
          );
        card.append(failures);
      }
    }
    return card;
  }
  function relationshipCheckView() {
    const card = append(
      el('section', 'card'),
      heading(
        'Do the relationships survive another execution?',
        'Checks equations against actual measured history. Call counts and marker order may differ; no cost prediction is made.'
      )
    );
    card.append(
      button(
        validationModel ? 'Choose another execution' : 'Check on another execution',
        () => send({ type: 'loadValidationReport' }),
        'secondary'
      )
    );
    if (!validationModel) return card;
    const key = JSON.stringify(proposals);
    if (
      relationshipCheckCache?.model !== loadedModel ||
      relationshipCheckCache.measured !== validationModel ||
      relationshipCheckCache.key !== key
    ) {
      const cache = (relationshipCheckCache = {
        model: loadedModel,
        measured: validationModel,
        key,
        pending: true
      });
      analysis
        .request('relationship-check', loadedModel, {
          measured: validationModel,
          options: { proposals }
        })
        .then((value) => {
          cache.value = value;
        })
        .catch((error) => {
          cache.error = error.message;
        })
        .finally(() => {
          cache.pending = false;
          if (relationshipCheckCache === cache && activeTab === 'relations') render();
        });
    }
    const cache = relationshipCheckCache;
    if (cache.pending) {
      card.append(el('p', 'analysis-pending', 'Checking state equations…'));
      return card;
    }
    if (cache.error) {
      card.append(el('p', 'notice warn', cache.error));
      return card;
    }
    const summary = cache.value.summary;
    card.append(
      el(
        'p',
        'relationship-check-summary',
        `${validationName}: ${summary.holds} hold, ${summary.fails} fail, ${summary.unavailable + summary['not-exercised']} unavailable or unexercised, ${summary['baseline-failed']} invalid on the baseline.`
      )
    );
    card.append(
      el(
        'p',
        'small muted',
        'Matching PCV names and schemas must retain their meaning. Agreement on a new run is evidence for that run, not a causal proof.'
      )
    );
    const rank = { fails: 0, 'baseline-failed': 1, unavailable: 2, 'not-exercised': 3, holds: 4 };
    for (const check of [...cache.value.checks].sort((a, b) => rank[a.status] - rank[b.status])) {
      const detail = el('details', 'relationship-check');
      detail.dataset.relationshipStatus = check.status;
      detail.open = check.status === 'fails' && summary.fails <= 5;
      detail.append(
        el(
          'summary',
          '',
          `${check.status}: ${check.equation}${check.changedExpressions.length ? ' · PCV expressions changed' : ''}`
        )
      );
      if (check.measured)
        detail.append(
          el(
            'p',
            'small',
            `${check.measured.calls - check.measured.mismatches}/${check.measured.calls} measured target calls match; ${check.baseline.calls} baseline calls checked.`
          )
        );
      if (check.missing.length)
        detail.append(
          el('p', 'notice warn', 'No matching PCV schema for: ' + check.missing.join(', '))
        );
      if (check.changedExpressions.length)
        detail.append(
          el(
            'p',
            'notice warn',
            'Source PCV expressions changed: ' +
              check.changedExpressions.map((t) => t.region + '.' + t.state).join(', ')
          )
        );
      for (const example of check.measured?.examples || [])
        detail.append(
          el(
            'p',
            'mono small',
            `call ${example.seq}: equation ${example.predicted}, measured ${example.expected}`
          )
        );
      card.append(detail);
    }
    return card;
  }
  function comparisonView() {
    const main = el('div');
    const intro = append(
      el('section', 'card'),
      heading(
        'Compare region interfaces',
        'Compare measured costs at exactly shared PCV states. This separates changes in a region’s cost from changes in the workload mix. Call order may differ.'
      )
    );
    append(
      intro,
      button(
        validationModel ? 'Choose another comparison report' : 'Choose comparison report',
        () => send({ type: 'loadValidationReport' }),
        'secondary'
      ),
      el(
        'p',
        'small muted',
        'Assumes PCV names retain their meaning across reports. Each shared state receives equal weight within its region. No region costs are added together, and these differences are not a significance test.'
      )
    );
    main.append(intro);
    if (!validationModel) return main;
    if (comparisonCache?.model !== model || comparisonCache.measured !== validationModel) {
      const cache = (comparisonCache = { model, measured: validationModel, pending: true });
      analysis
        .request('comparison', model, {
          measured: validationModel,
          options: { costBasis: rawCosts ? 'recorded' : 'calibrated' }
        })
        .then((value) => {
          cache.value = value;
        })
        .catch((error) => {
          cache.error = error.message;
        })
        .finally(() => {
          cache.pending = false;
          if (comparisonCache === cache && activeTab === 'compare') render();
        });
    }
    if (comparisonCache.pending) {
      main.append(el('p', 'analysis-pending', 'Comparing observed states…'));
      return main;
    }
    if (comparisonCache.error) {
      main.append(el('p', 'notice warn', comparisonCache.error));
      return main;
    }
    const comparison = comparisonCache.value;
    const card = append(el('section', 'card'), heading('Observed differences', validationName));
    const table = el('table', 'comparison-table');
    table.append(
      append(
        el('thead'),
        append(
          el('tr'),
          ...['Region', 'Shared states', 'Before', 'After', 'Difference'].map((text) =>
            el('th', '', text)
          )
        )
      )
    );
    const body = el('tbody');
    const rows = [...comparison.regions].sort(
      (a, b) => Math.abs(b.deltaMean || 0) - Math.abs(a.deltaMean || 0)
    );
    for (const row of rows) {
      const tr = el('tr');
      tr.dataset.comparisonRegion = row.region;
      append(
        tr,
        append(
          el('td'),
          model.regions.some((r) => r.id === row.region)
            ? button(row.name, () => choose(row.region, 'interface'), 'link-button')
            : el('span', '', row.name),
          el('small', 'muted', row.status),
          row.changedExpressions?.length ? badge('PCV expressions changed', 'warn') : null
        ),
        el(
          'td',
          'number',
          row.pairedStates
            ? `${row.pairedStates} (${row.beforeStates} → ${row.afterStates} observed)`
            : 'No paired states'
        ),
        el('td', 'number', row.beforeMean == null ? '—' : fmt(row.beforeMean)),
        el('td', 'number', row.afterMean == null ? '—' : fmt(row.afterMean)),
        el(
          'td',
          'number ' + (row.deltaMean > 0 ? 'increase' : row.deltaMean < 0 ? 'decrease' : ''),
          row.deltaMean == null ? '—' : `${row.deltaMean > 0 ? '+' : ''}${fmt(row.deltaMean)}`
        )
      );
      body.append(tr);
      if (!row.points.length && !row.beforeFormulas) continue;
      const detailRow = el('tr'),
        cell = el('td');
      cell.colSpan = 5;
      const detail = el('details');
      detail.append(el('summary', '', 'Inspect shared states and formulas'));
      if (row.changedExpressions?.length)
        detail.append(
          el(
            'p',
            'notice warn',
            'Source expressions changed for ' +
              row.changedExpressions.join(', ') +
              '. Check that these PCVs still have the same meaning before interpreting the comparison.'
          )
        );
      if (row.unsupportedStates)
        detail.append(
          el(
            'p',
            'notice warn',
            `${row.unsupportedStates} shared states have negative calibrated costs and are excluded. Inspect the recorded-count view.`
          )
        );
      for (const formula of row.beforeFormulas || [])
        detail.append(el('code', 'equation', 'Before: ' + formula));
      for (const formula of row.afterFormulas || [])
        detail.append(el('code', 'equation', 'After: ' + formula));
      for (const change of row.coefficientChanges || [])
        detail.append(
          el('p', 'mono small', `${change.state} coefficient: ${change.before} → ${change.after}`)
        );
      if (row.coefficientNote) detail.append(el('p', 'small muted', row.coefficientNote));
      for (const point of row.points.slice(0, 100))
        detail.append(
          el(
            'p',
            'mono small',
            `${stateLabel(row.states, point.state)}: ${fmt(point.before)} → ${fmt(point.after)} instructions/call (${point.beforeCalls} and ${point.afterCalls} calls)`
          )
        );
      if (row.points.length > 100)
        detail.append(
          el(
            'p',
            'small muted',
            `Showing 100 of ${row.points.length} paired states. The CLI comparison retains all states.`
          )
        );
      cell.append(detail);
      detailRow.append(cell);
      body.append(detailRow);
    }
    table.append(body);
    card.append(append(el('div', 'table-scroll'), table));
    main.append(card);
    return main;
  }
  function graphView(r,previousCard) {
    const graph=G.build(loadedModel), tree=G.hierarchy(loadedModel);
    const waitPairs=new Set(G.waits(graph).edges.map(e=>JSON.stringify([e.source,e.target]))).size;
    const card=el('section','card execution-graph');
    if(graph.status!=='observed') {card.append(el('p','notice warn',graph.warnings.join(' ')));return card;}
    const controls=el('div','execution-controls');
    const fullscreen=button(graphFullscreen?'Exit full screen':'Full-screen graph',()=>{
      graphFullscreen=!graphFullscreen;document.body.classList.toggle('graph-fullscreen',graphFullscreen);
      fullscreen.textContent=graphFullscreen?'Exit full screen':'Full-screen graph';
      send({type:'graphFullscreen',enabled:graphFullscreen});render();
    });
    fullscreen.textContent=graphFullscreen?'↙':'⛶';
    fullscreen.setAttribute('aria-label',graphFullscreen?'Exit full screen':'Full-screen graph');
    fullscreen.title=graphFullscreen?'Exit full screen':'Full-screen graph';
    const more=append(el('details','execution-more'),el('summary','','More'));
    const menu=el('div','execution-menu');more.append(menu);
    const actions=el('div','execution-menu-actions');menu.append(actions);
    append(controls,window.DrperfStandalone ? null : fullscreen,
      button('Expand all',()=>{graphMode='top';for(const n of tree.nodes.values())if(n.children.length)graphExpanded.add(n.key);render();},'execution-expand-all'));
    append(actions,
      button('Collapse all',()=>{graphExpanded.clear();render();}),
      button('Selected region',()=>{graphMode='region';render();}),
      button('Full graph',()=>{graphMode='top';render();}),
      button(`All waits (${waitPairs})`,()=>{graphMode='waits';render();},'execution-waits-button'));
    if(!window.DrperfStandalone) {
      actions.append(button('Export graph as HTML',()=>send({type:'exportGraphHtml',modelId:loadedModel.id,view:{selected,mode:graphMode,expanded:[...graphExpanded],showSequence:graphShowSequence}})));
      actions.append(button(graphSidebarOpen?'Hide region list':'Show region list',()=>{graphSidebarOpen=!graphSidebarOpen;render();}));
      actions.append(button('Reload profile',()=>send({type:'reload'})));
    }
    if(!window.DrperfStandalone && r.sources.length) actions.append(button('Open source',()=>send({type:'source',region:r.id,index:0}),'quiet'));
    actions.append(button(rawCosts?'View calibrated formulas':'View recorded counts',()=>{rawCosts=!rawCosts;model=rawCosts?M.recordedCosts(loadedModel):loadedModel;render();}));
    actions.append(button(graphShowSequence?'Hide sequence':'Show sequence',()=>{graphShowSequence=!graphShowSequence;render();}));
    menu.addEventListener('click',event=>{if(event.target.closest('button'))more.open=false;});
    const guide=append(el('details','execution-guide'),el('summary','','Legend and scope'),
      el('p','execution-legend','Nested boxes contain subregions. Optional gray arrows show observed sequence; dashed blue shows waits between distinct regions; red shows violated declarations; amber shows unverified declarations. Same-region synchronization is excluded from this graph.'));
    menu.append(guide);card.append(controls);
    if(graph.waitCoverage!=='observed')card.append(el('p','notice warn',graph.waitCoverage==='not captured'
      ?'Waits not captured. Enable DRPERF_WAITS=1.'
      :'Wait capture is incomplete. Producer edges are disabled.'));
    if(graph.eventChecks?.status!=='not captured' && graph.eventChecks) {
      const checks=graph.eventChecks;
      menu.append(el('p','execution-event-summary notice'+(checks.violations||checks.unverified?' warn':''),
        `Declared events: ${checks.status} · ${checks.probe?'delay probe':'baseline'} · ${checks.violations} violations · ${checks.unverified} unverified`));
    }
    const view=G.nestedView(tree,r.id,graphMode,graphExpanded);
    const waits=view.edges.filter(e=>e.kind==='wait');
    const visiblePairs=new Set(waits.map(e=>JSON.stringify([e.actualSource,e.actualTarget]))).size;
    menu.append(el('p','execution-wait-summary',waits.length
      ?`${visiblePairs} region relationships. Counts are repeated observations, not distinct dependencies or blocking stalls.`
      :`No matched waits in this view. All waits (${waitPairs}) shows dependencies elsewhere.`));
    menu.append(el('p','execution-scope',`${model.regions.length} regions in this profile · ${tree.roots.length} top-level regions · ${view.visible.size} visible boxes · ${graphMode==='top'?'Full graph':graphMode==='waits'?'Wait relationships':r.name}`));
    if(view.visible.size>250){card.append(el('p','notice warn','More than 250 visible boxes. Collapse all or select a smaller region.'));return card;}
    const regions=new Map(model.regions.map(n=>[n.id,n])), boxes=new Map(), headers=new Map();
    const ns='http://www.w3.org/2000/svg';
    const rootWidth=260;
    const stage=el('div','execution-measure');
    document.body.append(stage);
    function reveal(key){for(let n=tree.nodes.get(key);n?.parent;n=tree.nodes.get(n.parent))graphExpanded.add(n.parent);}
    const endpoints=e=>[tree.nodes.get(e.actualSource||e.source),tree.nodes.get(e.actualTarget||e.target)];
    const describe=e=>{
      const [source,target]=endpoints(e);
      return `${source.id} ${e.eventStatus?'declares wait on ('+e.eventStatus+')':e.kind==='wait'?'waits on':'then'} ${target.id} · ${e.observations} observations`;
    };
    const focusBox=key=>{
      const node=[...document.querySelectorAll('.execution-node')].find(n=>n.dataset.path===key);
      const canvas=document.querySelector('.execution-canvas');
      if(node&&canvas){const a=node.getBoundingClientRect(),b=canvas.getBoundingClientRect();
        if(a.top<b.top||a.top>b.bottom-60)canvas.scrollTop+=a.top-b.top-24;
        if(a.left<b.left||a.left>b.right-80)canvas.scrollLeft+=a.left-b.left-24;}
    };
    const openEdge=e=>{reveal(e.actualSource);reveal(e.actualTarget);graphHighlight=e.actualTarget;render();focusBox(e.actualTarget);};
    const selectNode=key=>{
      const node=tree.nodes.get(key);if(!node)return;
      graphHighlight=key;choose(node.id,'graph');
    };
    const selectChild=id=>{
      const parent=[...tree.nodes.values()].find(n=>n.id===r.id&&n.key===graphHighlight)
        ||[...tree.nodes.values()].find(n=>n.id===r.id);
      const key=parent?.children.find(k=>tree.nodes.get(k).id===id)
        ||[...tree.nodes.values()].find(n=>n.id===id)?.key;
      if(key){reveal(key);selectNode(key);focusBox(key);}
    };
    function makeHeader(key,width){
      const n=tree.nodes.get(key),target=regions.get(n.id),expanded=graphExpanded.has(key);
      const content=el('div','execution-box-header');content.style.width=(width-32)+'px';
      const title=el('div','execution-box-title');
      if(n.children.length){
        const toggle=button(expanded?'▾':'▸',()=>{
          graphToggleFocus={key,focus:document.activeElement===toggle};
          if(expanded)graphExpanded.delete(key);else graphExpanded.add(key);render();
        },'execution-toggle');
        toggle.setAttribute('aria-label',(expanded?'Collapse ':'Expand ')+target.name);
        toggle.setAttribute('aria-expanded',String(expanded));title.append(toggle);
      }
      const name=button(target.name,()=>selectNode(key),'execution-region-name');
      name.setAttribute('aria-label','Select region '+target.name);
      name.setAttribute('aria-pressed',String(r.id===target.id));
      title.append(name);content.append(title);
      stage.append(content);
      const bounds=content.getBoundingClientRect();
      headers.set(key,content);
      return {header:Math.ceil(bounds.height)+32};
    }
    const layoutNodes=new Map();
    function measure(key){
      const n=tree.nodes.get(key),children=graphExpanded.has(key)?n.children:[];
      const measured=makeHeader(key,rootWidth);
      boxes.set(key,{width:rootWidth,...measured});
      layoutNodes.set(key,{width:rootWidth,header:measured.header,children});
      children.forEach(measure);
    }
    try{view.roots.forEach(measure);}finally{stage.remove();}
    const routedEdges=view.edges.filter(e=>e.source!==e.target&&(e.kind==='wait'||graphShowSequence));
    const layoutKey=JSON.stringify([model.id,[...layoutNodes],routedEdges.map(e=>[e.source,e.target])]);
    graphLayoutRequest=layoutKey;
    let layout=graphLayouts.get(layoutKey);
    if(!layout){
      layout={pending:true};graphLayouts.set(layoutKey,layout);
      // Retain only a bounded set of expansion layouts; selecting a node reuses it.
      if(graphLayouts.size>24)graphLayouts.delete(graphLayouts.keys().next().value);
      window.DrperfLayout.layout(view.roots,layoutNodes,routedEdges).then(value=>{
        Object.assign(layout,{pending:false,value});if(activeTab==='graph'&&graphLayoutRequest===layoutKey)render();
      }).catch(error=>{Object.assign(layout,{pending:false,error:error.message});if(activeTab==='graph'&&graphLayoutRequest===layoutKey)render();});
    }
    if(layout.pending&&previousCard?.dataset.modelId===model.id){
      // Keep the actual old graph visible while ELK computes the new layout.
      // Disable stale controls briefly rather than replace it with a spinner.
      previousCard.setAttribute('aria-busy','true');
      previousCard.querySelectorAll('button').forEach(b=>b.disabled=true);
      return previousCard;
    }
    if(layout.pending||layout.error){
      card.append(el('p','execution-layout-status',layout.error?'Cannot lay out graph: '+layout.error:'Arranging regions with ELK…'));
      return card;
    }
    for(const [key,position]of layout.value.boxes)Object.assign(boxes.get(key),position);
    const {width,height}=layout.value;
    const svgEl=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;};
    const svg=svgEl('svg',{'class':'execution-svg',viewBox:`0 0 ${width} ${height}`,width,height,role:'img','aria-label':`Region graph for ${r.name}`});
    const defs=svgEl('defs');for(const kind of ['sequence','wait','violation','unverified']){
      const marker=svgEl('marker',{id:'execution-arrow-'+kind,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});
      marker.append(svgEl('path',{d:'M 0 0 L 10 5 L 0 10 z','class':'execution-arrow '+kind}));defs.append(marker);
    }svg.append(defs);
    function draw(key){
      const n=tree.nodes.get(key),b=boxes.get(key);
      const isSelected=n.id===r.id&&(!graphHighlight||tree.nodes.get(graphHighlight)?.id!==r.id||key===graphHighlight);
      const group=svgEl('g',{'class':'execution-node'+(isSelected?' selected':'')+(key===graphHighlight?' highlighted':''),
        'data-region':n.id,'data-path':key,role:'group',tabindex:0,'aria-label':'Region '+n.id,'aria-current':String(isSelected)});
      group.addEventListener('click',event=>{
        if(event.target.closest('button')||card.getAttribute('aria-busy')==='true')return;
        selectNode(key);
      });
      group.addEventListener('keydown',event=>{
        if(event.target!==group||card.getAttribute('aria-busy')==='true')return;
        if(event.key==='Enter'||event.key===' '){event.preventDefault();selectNode(key);}
      });
      group.append(svgEl('rect',{x:b.x,y:b.y,width:b.width,height:b.height,rx:8}));
      const foreign=svgEl('foreignObject',{x:b.x+16,y:b.y+16,width:b.width-32,height:b.header-32});
      foreign.append(headers.get(key));group.append(foreign);svg.append(group);
      if(graphExpanded.has(key))for(const child of n.children)draw(child);
    }view.roots.forEach(draw);
    for(const [i,e]of routedEdges.entries()){
      const [source,target]=endpoints(e),wait=e.kind==='wait';
      const style=e.eventStatus==='violation'?'violation':e.eventStatus==='unverified'?'unverified':e.kind;
      const sections=layout.value.routes.get(i)||[];
      const d=sections.map(points=>points.map((p,j)=>`${j?'L':'M'} ${p.x} ${p.y}`).join(' ')).join(' ');
      const attrs={d,'class':'execution-edge '+e.kind+' '+style,'data-kind':e.kind,'data-event-status':e.eventStatus||'',
        'data-source':source.id,'data-target':target.id,'marker-end':`url(#execution-arrow-${style})`};
      const line=svgEl('path',attrs);line.append(svgEl('title',{},describe(e)));svg.append(line);
      if(wait){
        const hit=svgEl('path',{...attrs,'class':'execution-edge-hit','marker-end':'',role:'button',tabindex:0,'aria-label':describe(e)});
        hit.addEventListener('click',()=>openEdge(e));
        hit.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();openEdge(e);}});svg.append(hit);
      }
    }
    const surface=append(el('div','execution-surface'),svg);
    const canvas=append(el('div','execution-canvas'),surface);
    let paddingX=0,paddingY=0;
    card.dataset.modelId=model.id;
    card.setAttribute('aria-busy','false');
    const zoomText=el('span','execution-zoom');
    const scale=()=>{
      svg.setAttribute('width',String(Math.round(width*graphZoom)));svg.setAttribute('height',String(Math.round(height*graphZoom)));
      surface.style.width=Math.round(width*graphZoom)+'px';surface.style.height=Math.round(height*graphZoom)+'px';
      zoomText.textContent=Math.round(graphZoom*100)+'%';
    };
    const zoomTo=value=>{
      const x=(canvas.scrollLeft+canvas.clientWidth/2-paddingX)/graphZoom,y=(canvas.scrollTop+canvas.clientHeight/2-paddingY)/graphZoom;
      graphZoom=Math.max(.005,Math.min(3,value));scale();
      canvas.scrollLeft=paddingX+x*graphZoom-canvas.clientWidth/2;canvas.scrollTop=paddingY+y*graphZoom-canvas.clientHeight/2;
    };
    const fitGraph=()=>{
      zoomTo(Math.min(1,(canvas.clientWidth-16)/width,(canvas.clientHeight-16)/height));
      canvas.scrollLeft=paddingX-Math.max(0,(canvas.clientWidth-width*graphZoom)/2);
      canvas.scrollTop=paddingY-Math.max(0,(canvas.clientHeight-height*graphZoom)/2);
    };
    const compactButton=(label,text,action)=>{
      const b=button(text,action);b.setAttribute('aria-label',label);b.title=label;return b;
    };
    const detailsToggle=compactButton(graphDetailsOpen?'Hide details':'Show details','Details',()=>{graphDetailsOpen=!graphDetailsOpen;render();});
    detailsToggle.setAttribute('aria-expanded',String(graphDetailsOpen));
    append(controls,compactButton('Fit graph','Fit',fitGraph),
      compactButton('Zoom out','−',()=>zoomTo(graphZoom/1.25)),zoomText,compactButton('Zoom in','+',()=>zoomTo(graphZoom*1.25)),detailsToggle,more);
    actions.append(button('100%',()=>zoomTo(1)));
    card.restoreGraphViewport=scroll=>{
      // Keep the scroll surface padded for navigation, without translating
      // the whole viewport to compensate for a changed node position.
      paddingX=canvas.clientWidth;paddingY=canvas.clientHeight;
      surface.style.padding=`${paddingY}px ${paddingX}px`;
      canvas.scrollLeft=scroll?scroll.canvasX+paddingX-(scroll.canvasWidth??paddingX):(paddingX-Math.max(0,(canvas.clientWidth-width*graphZoom)/2));
      canvas.scrollTop=scroll?scroll.canvasY+paddingY-(scroll.canvasHeight??paddingY):paddingY;
      if(graphAutoFit){fitGraph();graphAutoFit=false;}
      if(graphToggleFocus){
        const anchor=graphToggleFocus;
        const node=[...canvas.querySelectorAll('.execution-node')].find(n=>n.dataset.path===anchor.key);
        const toggle=node?.querySelector('.execution-toggle');
        if(toggle){
          if(anchor.focus)toggle.focus({preventScroll:true});
        }
        graphToggleFocus=null;
      }
    };
    scale();
    const secondary=(label,content)=>append(el('details','execution-secondary'),el('summary','',label),content);
    const inspector=append(el('aside','execution-inspector'),formulaCard(r,selectChild),
      secondary('Function breakdown',attribution(r)),secondary('Observed states',observations(r)));
    inspector.hidden=!graphDetailsOpen;
    inspector.setAttribute('aria-label','Selected region performance');
    const split=append(el('div','execution-split'+(graphDetailsOpen?'':' details-hidden')),canvas,inspector);
    card.append(split);menu.append(el('p','small muted','Arrows point from consumer to publisher. Top-level regions run horizontally; children stack vertically. Fit shows the overview; zoom in to read names. '+graph.contract));
    const details=el('details','execution-edge-details');details.open=true;details.append(el('summary','',`Relationships for ${r.name}`));
    for(const e of view.edges){
      const source=tree.nodes.get(e.actualSource||e.source),target=tree.nodes.get(e.actualTarget||e.target);
      if(source.id!==r.id&&target.id!==r.id&&tree.nodes.get(e.source)?.id!==r.id&&tree.nodes.get(e.target)?.id!==r.id)continue;
      const row=el('p','execution-edge-row');Object.assign(row.dataset,{kind:e.kind,source:source.id,target:target.id});
      row.textContent=`${source.path.join(' / ')} ${e.eventStatus?'declares wait on ('+e.eventStatus+')':e.kind==='wait'?'waits on completion from':'then'} ${target.path.join(' / ')} · ${e.observations} observations`;
      const global=graph.edges.find(g=>g.kind===e.kind&&g.source===source.id&&g.target===target.id&&g.eventStatus===e.eventStatus);
      const count=global&&G.countFormula(global);
      if(count!==null&&count!==undefined)row.append(el('span','small muted',` · full-profile count: ${count} per ${global.context} invocation`));
      if(e.kind==='wait'){
        const reveal=button('Reveal endpoints',()=>openEdge(e),'execution-reveal-wait');
        reveal.setAttribute('aria-label','Reveal wait: '+describe(e));
        reveal.dataset.eventStatus=e.eventStatus||'';row.append(reveal);
      }
      details.append(row);
    }inspector.insertBefore(details,inspector.children[1]);return card;
  }
  function render() {
    if(activeTab==='graph'&&renderedTab!=='graph')graphAutoFit=true;
    if(activeTab!=='graph'){graphToggleFocus=null;graphLayoutRequest=null;}
    const previousGraph=document.querySelector('.execution-graph');
    const viewportKey=JSON.stringify([model?.id,graphMode==='region'?selected:null,graphMode]);
    const graphScroll = activeTab==='graph' && renderedTab==='graph' && graphViewportKey===viewportKey
      ? {x:window.scrollX,y:window.scrollY,canvasX:document.querySelector('.execution-canvas')?.scrollLeft||0,
         canvasY:document.querySelector('.execution-canvas')?.scrollTop||0,
         canvasWidth:document.querySelector('.execution-canvas')?.clientWidth,canvasHeight:document.querySelector('.execution-canvas')?.clientHeight} : null;
    graphViewportKey=viewportKey;
    renderedTab=activeTab;
    if (activeTab!=='graph' && graphFullscreen) {
      graphFullscreen=false;
      send({type:'graphFullscreen',enabled:false});
    }
    document.body.classList.toggle('graph-fullscreen',graphFullscreen);
    document.body.classList.toggle('graph-active',activeTab==='graph');
    document.body.classList.toggle('graph-sidebar-open',graphSidebarOpen);
    root.replaceChildren();
    if (!model) {
      root.append(el('div', 'empty', 'Open a drperf report to explore its regions.'));
      return;
    }
    const top = el('header', 'topbar');
    append(
      top,
      append(
        el('div', 'brand'),
        el('span', 'brand-mark', 'd'),
        append(el('div'), el('strong', '', 'drperf'), el('span', 'muted', 'REGION EXPLORER'))
      ),
      append(
        el('div', 'top-meta'),
        el(
          'span',
          'muted',
          `${model.regions.length} regions · ${model.relations.length} relationships`
        ),
        button(
          rawCosts ? 'View calibrated formulas' : 'View recorded counts',
          () => {
            rawCosts = !rawCosts;
            model = rawCosts ? M.recordedCosts(loadedModel) : loadedModel;
            render();
          },
          'quiet'
        ),
        button('Reload', () => send({ type: 'reload' }), 'quiet')
      )
    );
    root.append(top);
    const errors = [...(model.validity?.errors || []), ...(model.validity?.traceErrors || [])];
    if (errors.length)
      root.append(
        el(
          'div',
          'notice error',
          'Measurement errors: ' + errors.join('; ') + '. Scenario predictions are disabled.'
        )
      );
    const shell = el('div', 'shell'),
      aside = el('aside', 'region-sidebar');
    aside.append(el('div', 'eyebrow', 'MEASURED REGIONS'));
    const search = el('input', 'search');
    search.type = 'search';
    search.placeholder = 'Find a region or PCV';
    search.value = filter;
    search.setAttribute('aria-label', 'Find a region or PCV');
    const list = el('nav', 'region-list');
    function fill() {
      list.replaceChildren();
      for (const r of model.regions.filter((r) =>
        (r.name + ' ' + r.states.join(' ')).toLowerCase().includes(filter.toLowerCase())
      )) {
        const b = button(
          '',
          () => choose(r.id),
          'region-button' + (r.id === selected ? ' active' : '')
        );
        b.setAttribute('aria-current', r.id === selected ? 'true' : 'false');
        const explanations = r.regimes.map((f) => M.interfaceExplanation(model, r.id, f));
        const unavailable = explanations.some((e) => e.share === null);
        const share = explanations.length && !unavailable
          ? Math.max(...explanations.map((e) => e.share)) : null;
        append(
          b,
          el('span', 'region-name', r.name),
          append(
            el('span', 'region-meta'),
            el('span', 'muted', r.states.join(', ') || 'no PCVs'),
            share === null
              ? badge(unavailable ? 'share unavailable' : 'needs states')
              : share > 0.05
                ? badge(`${unexplainedPercent(share)}% unexplained${explanations.some((e) => e.estimated) ? ' (estimate)' : ''}`, 'warn')
                : el('span', 'good-dot', '●')
          )
        );
        list.append(b);
      }
    }
    search.addEventListener('input', () => {
      filter = search.value;
      fill();
    });
    fill();
    append(
      aside,
      search,
      list,
      el(
        'p',
        'sidebar-note',
        'Each interface describes one region. There is no total-cost or latency estimate.'
      )
    );
    const content = el('main', 'content');
    const tabs = el('nav', 'tabs');
    tabs.setAttribute('aria-label', 'Explorer views');
    for (const [key, title] of [
      ['interface', 'Interface'],
      ['graph', 'Graph'],
      ['relations', 'Relationships'],
      ['scenario', 'What-if'],
      ['compare', 'Compare runs']
    ]) {
      const b = button(
        title,
        () => {
          activeTab = key;
          persist();
          render();
        },
        'tab' + (activeTab === key ? ' active' : '')
      );
      b.setAttribute('aria-selected', String(activeTab === key));
      tabs.append(b);
    }
    content.append(tabs);
    const r = region();
    if (!r) {
      content.append(el('p', 'empty', 'No application regions in this report.'));
    } else {
      selected = r.id;
      content.append(
        activeTab === 'interface'
          ? interfaceView(r)
          : activeTab === 'graph'
            ? graphView(r,previousGraph)
          : activeTab === 'relations'
            ? relationshipsView()
            : activeTab === 'compare'
              ? comparisonView()
              : scenarioView()
      );
    }
    append(shell, aside, content);
    root.append(shell);
    if(graphScroll){window.scrollTo(graphScroll.x,graphScroll.y);const canvas=document.querySelector('.execution-canvas');
      if(canvas){canvas.scrollLeft=graphScroll.canvasX;canvas.scrollTop=graphScroll.canvasY;}}
    const currentGraph=document.querySelector('.execution-graph');
    if(currentGraph?.getAttribute('aria-busy')==='false')currentGraph.restoreGraphViewport?.(graphScroll);
    if (activeTab === 'scenario') updateScenario();
    persist();
  }
  window.addEventListener('message', (event) => {
    const message = event.data;
    if (message?.type === 'model') {
      try {
        const previousId = model?.id;
        ++scenarioGeneration;
        scenarioCache = null;
        comparisonCache = null;
        proposalModelCache = null;
        experimentCache = null;
        relationshipCheckCache = null;
        loadedModel = M.validate(message.model);
        model = rawCosts ? M.recordedCosts(loadedModel) : loadedModel;
        const current = host?.getState() || saved;
        const same = current.modelId === model.id;
        selected = message.selected || (same ? current.selected : null) || model.regions[0]?.id;
        if (previousId !== model.id) {
          graphAutoFit=true;
          graphHistory.length = 0;graphToggleFocus=null;graphLayoutRequest=null;
          graphExpanded.clear(); graphHighlight=null; graphZoom=1;
          graphMode = 'top';
          if(window.DrperfStandalone) {
            const view=window.DrperfStandalone;
            graphShowSequence=view.showSequence===true;
            if(['top','region','waits'].includes(view.mode))graphMode=view.mode;
            if(Array.isArray(view.expanded))for(const key of view.expanded)if(typeof key==='string')graphExpanded.add(key);
          }
          sourceStatuses.clear();
          validationModel = null;
          proposalResult = null;
          proposalDraft = null;
          proposals = same && Array.isArray(current.proposals) ? current.proposals : [];
          edits = same && Array.isArray(current.edits) ? current.edits : [];
          assumptionIds = same && Array.isArray(current.assumptionIds) ? current.assumptionIds : [];
        }
        render();
      } catch (error) {
        root.replaceChildren(el('div', 'notice error', 'Cannot display report: ' + error.message));
      }
    } else if (message?.type === 'scenario' && message.modelId === loadedModel?.id) {
      const generation = ++scenarioImportGeneration,
        source = loadedModel,
        scenario = message.scenario;
      const analysisGeneration = ++scenarioGeneration;
      scenarioCache = null;
      scenarioPending = true;
      result = null;
      analysis
        .request('scenario', source, { scenario, measured: message.measured })
        .then((response) => {
          if (
            generation !== scenarioImportGeneration ||
            analysisGeneration !== scenarioGeneration ||
            source !== loadedModel
          )
            return;
          rawCosts = scenario.costBasis === 'recorded';
          model = rawCosts ? M.recordedCosts(source) : source;
          edits = structuredClone(scenario.edits);
          assumptionIds = [...scenario.relations];
          proposals = structuredClone(scenario.proposals || []);
          auditAlternatives = !!scenario.auditAlternatives;
          selected = edits[0]?.region || selected;
          validationModel = message.measured ? M.validate(message.measured) : null;
          validationName = message.measuredName || 'Measured report';
          proposalModelCache = null;
          proposalDraft = null;
          proposalResult = null;
          activeTab = 'scenario';
          result = response.result;
          scenarioPending = false;
          scenarioError = '';
          scenarioValidation = response.validation || null;
          scenarioValidationError = response.validationError || '';
          scenarioCache = {
            model,
            measured: validationModel,
            key: JSON.stringify(currentScenario())
          };
          render();
          send({
            type: 'analysisFinished',
            baseModelId: source.id,
            modelId: result.modelId,
            backend: analysis.backend,
            validationStructureMatches: scenarioValidation?.structureMatches,
            validationMeasuredId: scenarioValidation?.measuredModelId,
            changedRegions: result.regions.filter((r) => r.changedCalls).map((r) => r.region)
          });
        })
        .catch((error) => {
          if (
            generation !== scenarioImportGeneration ||
            analysisGeneration !== scenarioGeneration ||
            source !== loadedModel
          )
            return;
          scenarioPending = false;
          scenarioError = error.message;
          send({
            type: 'analysisFinished',
            baseModelId: source.id,
            error: error.message,
            backend: analysis.backend
          });
          root.prepend(el('p', 'notice warn', 'Cannot open saved scenario: ' + error.message));
        });
    } else if (message?.type === 'sourceStatus' && message.modelId === loadedModel?.id) {
      if (JSON.stringify(sourceStatuses.get(message.region)) === JSON.stringify(message.sources || [])) return;
      sourceStatuses.set(message.region, message.sources || []);
      if (activeTab === 'interface' && selected === message.region) {
        const scroll = {x:window.scrollX,y:window.scrollY};
        render();window.scrollTo(scroll.x,scroll.y);
      }
    } else if (message?.type === 'validationModel') {
      try {
        validationModel = M.validate(message.model);
        validationName = message.name || 'Measured report';
        if (activeTab === 'compare' || activeTab === 'relations') render();
        else updateScenario();
      } catch (error) {
        scenarioError = error.message;
        updateScenario();
      }
    } else if (message?.type === 'select' && model?.regions.some((r) => r.id === message.region)) {
      if (selected === message.region) return;
      selected = message.region;
      render();
    }
  });
  document.addEventListener('pointerdown',event=>{
    const menu=document.querySelector('.execution-more[open]');
    if(menu&&!menu.contains(event.target))menu.open=false;
  });
  document.addEventListener('keydown',event=>{
    const menu=document.querySelector('.execution-more[open]');
    if(event.key==='Escape'&&menu){menu.open=false;menu.querySelector('summary').focus();return;}
    if(event.key==='Escape'&&graphFullscreen&&!window.DrperfStandalone) {
      graphFullscreen=false;
      document.body.classList.remove('graph-fullscreen');
      send({type:'graphFullscreen',enabled:false});
      const button=document.querySelector('.execution-controls button');
      if(button)button.textContent='Full-screen graph';
      render();
    }
  });
  render();
  send({ type: 'ready' });
})();
