"""Region-only summaries of observed sequencing, nesting, and wait dependencies.

Execution contexts are used internally to avoid inventing order between
independent executions. They are not graph nodes. Costs remain exclusive
per-invocation interfaces; this summary is not a schedule or a latency model.
"""
from collections import Counter, defaultdict
import json
import subprocess
import html
import textwrap

import composition


def invocation(event):
    return (event['group'], str(event.get('thread', event.get('tid'))),
            int(event.get('seq', event.get('regionSeq', 0))))


def build(model, root=None, max_depth=None):
    from report_storage import require_inline_waits
    require_inline_waits(model)
    regions = {r['id']: r for r in model['regions']}
    result = {'status': 'observed', 'root': root, 'nodes': [], 'edges': [], 'warnings': [],
              'sourceRoot': model.get('provenance', {}).get('sourceRoot', ''),
              'workload': model.get('provenance', {}).get('experiment', ''),
              'waitCoverage': model.get('waits', {}).get('status', 'not captured'),
              'declaredEventsIncluded': True,
              'eventChecks': {'status': model.get('eventModel', {}).get('status', 'not captured'),
                              'probe': bool(model.get('eventModel', {}).get('probe')),
                              'violations': len(model.get('eventModel', {}).get('violations', [])),
                              'unverified': len(model.get('eventModel', {}).get('unverified', []))},
              'contract': 'Solid edges are observed next-sibling order, not proof of a required dependency. '
                          'Nesting is separate. Wait edges target completion inside a consumer, not its entry. '
                          'Only regions are shown; cycles can summarize repeated invocations. '
                          'Costs are exclusive state-wise mean instructions per invocation and are never charged per edge. '
                          'Sync-call counts do not establish time blocked. '
                          'Declared event edges check observed publish/waited order; violations are rejected claims, not dependencies. '
                          'Unmarked work between siblings is not assumed free. No critical-path latency is inferred.'}
    errors = list(model.get('validity', {}).get('errors', [])) + list(model.get('validity', {}).get('traceErrors', []))
    if not model.get('trace', {}).get('complete'):
        errors.append('Complete region trace required.')
    if root is not None and root not in regions:
        raise ValueError('Unknown root region: '+root)
    if errors:
        result.update(status='unavailable', warnings=errors)
        return result
    traces = sorted(model['trace']['events'], key=lambda t: (t['group'], int(t['seq'])))
    try:
        forest = composition._forest(regions, traces)
    except (ValueError, KeyError, TypeError) as error:
        result.update(status='unavailable', warnings=[str(error)])
        return result
    by_key, roots, parent = {}, defaultdict(list), {}
    for node, trace in zip(forest, traces):
        node['trace'], node['uid'] = trace, invocation(trace)
        by_key[node['uid']] = node
        for child in node['children']:
            parent[id(child)] = node
    for node in forest:
        if id(node) not in parent:
            roots[(node['trace']['group'], str(node['trace']['thread']))].append(node)
    chosen, depths = set(), {}
    for node in forest:
        ancestor = parent.get(id(node))
        depth = (0 if root is None or node['region'] == root else
                 depths.get(id(ancestor), -2) + 1)
        if depth >= 0 and (max_depth is None or depth <= max_depth):
            chosen.add(id(node))
            depths[id(node)] = depth
    primary = [n for n in forest if id(n) in chosen]
    by_region = defaultdict(list)
    for node in primary:
        by_region[node['region']].append(node)
    links = {}

    def add(kind, source, target, context, owner, evidence=None, event_status=None):
        key = kind, source, target, context, event_status
        edge = links.setdefault(key, {'kind': kind, 'source': source, 'target': target,
                                     'context': context, 'observations': 0, '_counts': Counter(),
                                     'evidence': []})
        if event_status:
            edge.update(origin='declared-event', eventStatus=event_status)
        edge['observations'] += 1
        if owner:
            edge['_counts'][owner['uid']] += 1
        if evidence and len(edge['evidence']) < 8:
            edge['evidence'].append(evidence)

    for node in primary:
        for child in node['children']:
            if id(child) in chosen:
                add('contains', node['region'], child['region'], node['region'], node)
        for first, second in zip(node['children'], node['children'][1:]):
            if id(first) in chosen and id(second) in chosen:
                add('sequence', first['region'], second['region'], node['region'], node)
    if root is None:
        for siblings in roots.values():
            for first, second in zip(siblings, siblings[1:]):
                add('sequence', first['region'], second['region'], None, None)

    report = model.get('waits', {})
    events = {e['id']: e for e in report.get('events', [])}
    wait_summary = defaultdict(Counter)
    dependency_nodes = set()
    for operation in report.get('operations', []):
        consumer = by_key.get(invocation(operation))
        if not consumer or id(consumer) not in chosen:
            continue
        summary = wait_summary[consumer['region']]
        summary[operation['api']] += 1
        found = False
        if report.get('status') == 'observed':
            for producer_id in operation.get('producers', []):
                event = events.get(producer_id)
                producer = by_key.get(invocation(event)) if event else None
                if not producer:
                    continue
                if producer['region'] == consumer['region']:
                    found = True
                    continue
                dependency_nodes.add(producer['region'])
                # Arrows read "consumer waits on work from producer", not CPU return-before-entry.
                add('wait', consumer['region'], producer['region'], consumer['region'], consumer,
                    {'operation': operation['id'], 'producer': producer_id,
                     'basis': operation['dependency']})
                found = True
        if not found:
            summary['<unresolved>'] += 1
    if report.get('status') == 'observed':
        for claim in model.get('eventModel', {}).get('edges', []):
            consumer_event = events.get(claim.get('waited', claim.get('end')))
            producer_event = events.get(claim.get('publication'))
            consumer = by_key.get(invocation(consumer_event)) if consumer_event else None
            producer = by_key.get(invocation(producer_event)) if producer_event else None
            if not consumer or not producer or id(consumer) not in chosen or consumer['region'] == producer['region']:
                continue
            status = claim['status']
            if status not in ('ordered', 'violation', 'unverified'):
                continue
            dependency_nodes.add(producer['region'])
            add('wait', consumer['region'], producer['region'], consumer['region'], consumer,
                {'operation': consumer_event['id'], 'producer': producer_event['id'],
                 'basis': 'declared-event', 'event': claim['event'],
                 'generation': claim['generation'], 'status': status}, status)
    for name in sorted(set(by_region) | dependency_nodes):
        region = regions[name]
        result['nodes'].append({'id': name, 'name': region.get('name', name),
                                'calls': len(by_region.get(name, [])),
                                'dependencyOnly': name not in by_region,
                                'hiddenChildren': sorted({c['region'] for n in by_region.get(name, [])
                                                          for c in n['children'] if id(c) not in chosen}),
                                'states': region['states'],
                                'ownFits': [{'coefficients': f['coefficients'], 'constant': f['constant'],
                                             'range': f.get('range', []),
                                             'unexplainedFunctions': f.get('attribution', {}).get('unexplained', []),
                                             'unexplainedShare': f.get('unexplainedShare', 0)}
                                            for f in region.get('regimes', [])],
                                'costBasis': 'exclusive CPU instructions per invocation; full-profile fit',
                                'sources': region.get('sources', []),
                                'waitOperations': dict(wait_summary.get(name, {}))})
    for key, edge in sorted(links.items(), key=lambda p: repr(p[0])):
        calls = by_region.get(edge['context'], [])
        counts = edge.pop('_counts')
        states = regions[edge['context']]['states'] if edge['context'] else []
        edge['states'] = states
        edge['perInvocation'] = composition.affine([n['state'] for n in calls],
                                                   [counts[n['uid']] for n in calls], states) if calls else None
        edge['invocationsChecked'] = len(calls)
        result['edges'].append(edge)
    return result


def formula(node, fit):
    terms = []
    for coefficient, state in zip(fit['coefficients'], node['states']):
        if round(coefficient):
            terms.append(f'{round(coefficient)}*{state}')
    if fit['constant'] or not terms:
        terms.append(str(round(fit['constant'])))
    text = ' + '.join(terms).replace('+ -', '- ')
    if fit['unexplainedShare']:
        text += ' + unexplained'
    return text


def dot(graph):
    q = json.dumps
    ids = {n['id']: f'r{i}' for i, n in enumerate(graph['nodes'])}
    lines = ['digraph drperf {', 'rankdir=TB;',
             'graph [bgcolor="white",pad="0.3",nodesep="0.4",ranksep="0.8",fontname="Arial"];',
             'node [shape=box,style="rounded,filled",fillcolor="#f3f6fa",color="#60758b",fontname="Arial",fontsize=11];',
             'edge [fontname="Arial",fontsize=9,color="#425873"];']
    for node in graph['nodes']:
        fits = node['ownFits']
        cost = formula(node, fits[0]) if len(fits) == 1 else f'{len(fits)} cost regimes' if fits else 'no cost fit'
        label = node['name']+'\nown: '+'\n'.join(textwrap.wrap(cost, 65, break_long_words=False))
        label += '\n'+('external to selected path' if node['dependencyOnly'] else f'{node["calls"]} observed calls')
        if node.get('hiddenChildren'):
            label += f'\n{len(node["hiddenChildren"])} nested regions (click to explore)'
        unknown = node['waitOperations'].get('<unresolved>', 0)
        if unknown:
            label += f'\n{unknown} sync calls: producer unresolved'
        lines.append(f'{ids[node["id"]]} [id={q(ids[node["id"]])},label={q(label)},'
                     f'color={q("#b56c10" if unknown else "#60758b")}];')
    for edge in graph['edges']:
        rel = edge['perInvocation']
        count = composition.affine_text(rel, edge['states']) if rel else None
        if edge['kind'] == 'contains':
            label = 'contains'+(f' x ({count})' if count not in (None, '1') else '')
            style = 'style=dotted,color="#9ba8b7",constraint=false'
        elif edge['kind'] == 'sequence':
            label = 'then'
            if count not in (None, '1'):
                label += f' x ({count}) / {edge["context"]}'
            style = 'style=solid'
        else:
            label = 'waits on work from'+(f' x ({count})' if count is not None else '')
            style = 'style=dashed,color="#176ac1",fontcolor="#176ac1",constraint=false'
            if edge.get('eventStatus'):
                label = 'declared wait: '+edge['eventStatus']+(f' x ({count})' if count is not None else '')
                color = {'ordered': '#176ac1', 'violation': '#c62828', 'unverified': '#b56c10'}[edge['eventStatus']]
                style = f'style=dashed,color="{color}",fontcolor="{color}",constraint=false'
        if edge['context'] and rel is None:
            label += '\ncount not affine in declared PCVs'
        if edge['kind'] != 'contains':
            label += f'\n{edge["observations"]} observations'
        lines.append(f'{ids[edge["source"]]} -> {ids[edge["target"]]} [label={q(label)},{style}];')
    lines.append('}')
    return '\n'.join(lines)


def svg(graph):
    result = subprocess.run(['dot', '-Tsvg'], input=dot(graph), text=True,
                            capture_output=True, check=True)
    return result.stdout[result.stdout.index('<svg'):]


def write_html(graphs, destination, title='drperf region graph'):
    """Self-contained SVG graphs and clickable region details; no external assets."""
    data = [{'graph': g, 'svg': svg(g)} for g in graphs]
    payload = json.dumps(data).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = r'''<!doctype html><meta charset="utf-8"><title>TITLE</title>
<style>
body{margin:0;font:14px system-ui;color:#203349;background:#f5f7fa}header{padding:16px 22px;background:white;border-bottom:1px solid #dce2eb}h1{font-size:20px;margin:0 0 10px}select,button{padding:6px;margin-right:8px}main{display:grid;grid-template-columns:minmax(0,1fr) 360px;height:calc(100vh - 130px)}#canvas{overflow:auto;background:white;padding:20px}#details{overflow:auto;padding:18px;border-left:1px solid #dce2eb}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px ui-monospace,monospace}small{color:#58697b}g.node{cursor:pointer}g.node:hover path,g.node:hover polygon{stroke:#176ac1;stroke-width:3}#note{margin-top:8px;font-size:12px;color:#58697b}
</style><header><h1>TITLE</h1><select id="view"></select><button id="back">Back</button><button id="fit">Fit</button><button id="smaller">−</button><button id="larger">+</button><small>Solid: observed sequence · Dotted: nesting · Blue dashed: waits on work from</small><div id="note"></div></header>
<main><div id="canvas"></div><aside id="details">Click a region to inspect its cost and wait operations.</aside></main>
<script>
const views=PAYLOAD;let active=0,zoom=1;const history=[];const select=document.getElementById('view'),canvas=document.getElementById('canvas');
views.forEach((v,i)=>{let o=document.createElement('option');o.value=i;o.textContent=v.graph.root||'All regions';select.append(o)});
function show(){const g=views[active].graph;canvas.innerHTML=views[active].svg;zoom=1;document.getElementById('note').textContent=(g.workload?g.workload+' · ':'')+'Observed states only. Wait capture: '+g.waitCoverage+'. Coefficients rounded for display.';document.getElementById('details').textContent='Click a region to inspect its cost and wait operations.'}
function navigate(i){history.push(active);active=i;select.value=String(i);show();fit()}
select.onchange=()=>navigate(Number(select.value));
document.getElementById('back').onclick=()=>{if(history.length){active=history.pop();select.value=String(active);show();fit()}};
function scale(f){zoom*=f;const s=canvas.querySelector('svg');s.style.width=(parseFloat(s.getAttribute('width'))*zoom)+'pt';s.style.height=(parseFloat(s.getAttribute('height'))*zoom)+'pt'}
function fit(){const s=canvas.querySelector('svg');scale(Math.min(1,(canvas.clientWidth-40)/(parseFloat(s.getAttribute('width'))*4/3))/zoom)}
document.getElementById('fit').onclick=fit;
document.getElementById('smaller').onclick=()=>scale(.8);document.getElementById('larger').onclick=()=>scale(1.25);
function cost(n,f){const terms=f.coefficients.flatMap((c,i)=>Math.round(c)?[Math.round(c)+'*'+n.states[i]]:[]);if(f.constant||!terms.length)terms.push(String(Math.round(f.constant)));return terms.join(' + ').replaceAll('+ -','- ')+(f.unexplainedShare?' + unexplained':'')}
canvas.onclick=event=>{let target=event.target.closest('g.node');if(!target)return;const g=views[active].graph;let n=g.nodes[Number(target.id.slice(1))];if(!n)return;const p=document.getElementById('details');p.replaceChildren();let h=document.createElement('h2');h.textContent=n.name;p.append(h);const next=views.findIndex(v=>v.graph.root===n.id);if(next>=0&&next!==active){const b=document.createElement('button');b.textContent='Explore this region';b.onclick=()=>navigate(next);p.append(b)}let pre=document.createElement('pre');const lines=[n.dependencyOnly?'Producer outside this view':n.calls+' observed calls in this view','PCVs: '+(n.states.join(', ')||'none'),'','Exclusive mean CPU instructions per invocation (observed states; displayed coefficients rounded):'];n.ownFits.forEach(f=>{lines.push(cost(n,f));lines.push('Unexplained share: '+Math.round(100*f.unexplainedShare)+'%');lines.push('Observed ranges: '+n.states.map((s,i)=>s+'=['+(f.range[i]||[]).map(Math.round).join(', ')+']').join('; '));(f.unexplainedFunctions||[]).forEach(row=>lines.push('  '+row.function+': '+Math.round(row.instructions)+' instructions'))});lines.push('','Wait operations:');Object.entries(n.waitOperations).forEach(([api,count])=>lines.push(api+': '+count));if(!Object.keys(n.waitOperations).length)lines.push('None captured in this region.');lines.push('','Relationships:');g.edges.filter(e=>e.source===n.id||e.target===n.id).forEach(e=>lines.push(e.source+' — '+e.kind+' → '+e.target+' ('+e.observations+' observations)'));lines.push('','Source root: '+g.sourceRoot);n.sources.forEach(s=>lines.push(typeof s==='string'?s:s.path+':'+s.line));lines.push('',g.contract);pre.textContent=lines.join('\n');p.append(pre)};show();fit();
</script>'''
    destination.write_text(page.replace('TITLE', html.escape(title)).replace('PAYLOAD', payload))
