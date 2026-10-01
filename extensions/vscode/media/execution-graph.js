/* Region-only graph data and deterministic layout. No report expressions or
 * generated markup are executed. Older reports use their complete marker trace;
 * exported graphs additionally carry the checker's affine edge-count formulas. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DrperfGraph = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const cache = new WeakMap();
  const uid = (e) => JSON.stringify([e.group, String(e.thread ?? e.tid), e.regionSeq ?? e.seq]);
  const contract = 'Sequence means observed consecutive siblings, not a required dependency. '
    + 'Wait arrows point from consumer to the region that published completion. '
    + 'Counts cover all captured invocations, including already-satisfied waits. '
    + 'Regions aggregate execution contexts; cycles can represent repeated calls. '
    + 'This is not a latency or critical-path model.';
  // Resolve the exact captured invocations, never just region names or proximity.
  function declaredPairs(model) {
    if(model.waits?.status!=='observed')return [];
    const events=new Map((model.waits.events||[]).map(e=>[e.id,e]));
    return (model.eventModel?.edges||[]).flatMap(claim=>{
      const consumer=events.get(claim.waited??claim.end),producer=events.get(claim.publication);
      if(!consumer||!producer||!['ordered','violation','unverified'].includes(claim.status))return [];
      return [{consumer,producer,origin:'declared-event',eventStatus:claim.status}];
    });
  }
  function eventChecks(model) {
    const e=model.eventModel;
    return {status:e?.status||'not captured',probe:!!e?.probe,
      violations:e?.violations?.length||0,unverified:e?.unverified?.length||0};
  }
  function unavailable(reason) {
    return {status: 'unavailable', nodes: [], edges: [], warnings: [reason], contract};
  }
  function build(model) {
    if (cache.has(model)) return cache.get(model);
    let graph;
    try { graph = collect(model); }
    catch (error) { graph = unavailable(error.message); }
    cache.set(model, graph);
    return graph;
  }
  function collect(model) {
    if (!model.trace?.complete || model.validity?.errors?.length || model.validity?.traceErrors?.length)
      return unavailable('A complete, valid region trace is required. Re-export complete measurements to enable the graph.');
    const regions = new Map(model.regions.map(r => [r.id, r]));
    const exported = model.executionGraph;
    if (exported) {
      if (exported.status !== 'observed') return unavailable((exported.warnings || []).join('; ') || 'Graph unavailable.');
      if (!Array.isArray(exported.nodes) || !Array.isArray(exported.edges)
          || exported.nodes.length !== regions.size || exported.edges.length > 200000)
        throw Error('Invalid exported graph.');
      const ids = new Set();
      for (const n of exported.nodes) {
        if (!regions.has(n.id) || ids.has(n.id)) throw Error('Graph node does not match a profile region.');
        ids.add(n.id);
      }
      for (const e of exported.edges) {
        if (!ids.has(e.source) || !ids.has(e.target) || !['contains', 'sequence', 'wait'].includes(e.kind)
            || !Number.isSafeInteger(e.observations) || e.observations < 1
            || (e.context !== null && !ids.has(e.context))
            || (e.eventStatus && !['ordered','violation','unverified'].includes(e.eventStatus))) throw Error('Invalid exported graph edge.');
        if (e.perInvocation) {
          const rational = v => typeof v === 'string' && /^-?\d{1,128}(?:\/[1-9]\d{0,127})?$/.test(v);
          if (!Array.isArray(e.states) || e.states.some(s => !regions.get(e.context)?.states.includes(s))
              || !Array.isArray(e.perInvocation.coefficients)
              || e.perInvocation.coefficients.length !== e.states.length
              || !e.perInvocation.coefficients.every(rational) || !rational(e.perInvocation.constant))
            throw Error('Invalid edge-count formula.');
        }
      }
      const extra=new Map();
      if(!exported.declaredEventsIncluded)for(const pair of declaredPairs(model)) {
        const source=pair.consumer.region,target=pair.producer.region;
        if(!ids.has(source)||!ids.has(target))continue;
        const key=JSON.stringify([source,target,pair.eventStatus]);
        if(!extra.has(key))extra.set(key,{kind:'wait',source,target,context:source,observations:0,
          origin:pair.origin,eventStatus:pair.eventStatus});
        extra.get(key).observations++;
      }
      return {...exported, contract, eventChecks:eventChecks(model), edges: [...exported.edges,...extra.values()].filter(e =>
        e.kind !== 'wait' || (model.waits?.status === 'observed' && e.source !== e.target)),
        waitCoverage: model.waits?.status || 'not captured'};
    }
    // No reprofile needed for older portable reports. Validate the forest and
    // counter coverage before establishing any observed order.
    const events = [...model.trace.events].sort((a,b) =>
      a.group.localeCompare(b.group) || a.seq-b.seq);
    const stacks = new Map(), roots = new Map(), byInvocation = new Map();
    const nodes = [], counts = new Map(), boundaries = new Set();
    const stateKey = (r, values) => JSON.stringify([r.id, r.states.map((s,i) =>
      BigInt(Array.isArray(values) ? values[i] : values[s]).toString())]);
    for (const t of events) {
      const r = regions.get(t.region);
      if (!r || !Number.isSafeInteger(t.seq) || !Number.isSafeInteger(t.end) || t.end <= t.seq
          || r.states.length !== Object.keys(t.values).length) throw Error('Invalid region trace.');
      for (const boundary of [t.seq,t.end]) {
        const k = JSON.stringify([t.group,boundary]);
        if (boundaries.has(k)) throw Error('Duplicate region boundary.');
        boundaries.add(k);
      }
      const key = stateKey(r,t.values);
      counts.set(key,(counts.get(key)||0)+1);
      const context = JSON.stringify([t.group,t.thread]);
      if (!stacks.has(context)) { stacks.set(context,[]); roots.set(context,[]); }
      const stack = stacks.get(context);
      while (stack.length && stack.at(-1).end < t.seq) stack.pop();
      if (stack.length && t.end >= stack.at(-1).end) throw Error('Crossing region boundaries.');
      const node = {...t, children: []};
      (stack.length ? stack.at(-1).children : roots.get(context)).push(node);
      stack.push(node); nodes.push(node); byInvocation.set(uid(t),node);
    }
    for (const r of regions.values()) {
      let calls = 0;
      if (r.droppedCalls) throw Error('Some region calls were omitted.');
      for (const p of r.points) {
        const k = stateKey(r,p.state);
        if (counts.get(k) !== p.calls) throw Error('Trace and per-state counts disagree.');
        counts.delete(k); calls += p.calls;
      }
      if (calls !== r.calls) throw Error('Region call counts disagree.');
    }
    if (counts.size) throw Error('Trace contains unmatched calls.');
    const edges = new Map();
    function add(kind, source, target, context, meta={}) {
      const key = JSON.stringify([kind,source,target,context,meta.eventStatus]);
      if (!edges.has(key)) edges.set(key,{kind,source,target,context,observations:0,...meta});
      edges.get(key).observations++;
    }
    function sequence(siblings, context) {
      for (let i=1;i<siblings.length;i++)
        add('sequence',siblings[i-1].region,siblings[i].region,context);
    }
    for (const n of nodes) {
      for (const c of n.children) add('contains',n.region,c.region,n.region);
      sequence(n.children,n.region);
    }
    for (const siblings of roots.values()) sequence(siblings,null);
    const summaries = new Map([...regions.keys()].map(id => [id,{}]));
    const publications = new Map((model.waits?.events||[]).map(e => [e.id,e]));
    for (const op of model.waits?.operations||[]) {
      const consumer = byInvocation.get(uid(op));
      if (!consumer) continue;
      const summary = summaries.get(consumer.region);
      summary[op.api] = (summary[op.api]||0)+1;
      let matched = false;
      if (model.waits.status === 'observed') for (const id of op.producers||[]) {
        const pub = publications.get(id), producer = pub && byInvocation.get(uid(pub));
        if (!producer) continue;
        if (consumer.region===producer.region) { matched=true; continue; }
        add('wait',consumer.region,producer.region,consumer.region); matched = true;
      }
      if (!matched) summary['<unresolved>'] = (summary['<unresolved>']||0)+1;
    }
    for(const pair of declaredPairs(model)) {
      const consumer=byInvocation.get(uid(pair.consumer)),producer=byInvocation.get(uid(pair.producer));
      if(consumer&&producer&&consumer.region!==producer.region)add('wait',consumer.region,producer.region,consumer.region,
        {origin:pair.origin,eventStatus:pair.eventStatus});
    }
    return {status:'observed', contract, eventChecks:eventChecks(model), warnings:[], waitCoverage:model.waits?.status||'not captured',
      countFormulas:false, nodes:[...regions.values()].map(r => ({id:r.id,calls:r.calls,
        waitOperations:summaries.get(r.id)})), edges:[...edges.values()]};
  }
  function focus(graph, selected = null) {
    // Containment selects a level; it is never drawn as an execution edge.
    // A region can occur both nested and at the top level in different calls.
    const nestedCalls = new Map();
    for (const e of graph.edges) if (e.kind === 'contains')
      nestedCalls.set(e.target, (nestedCalls.get(e.target) || 0) + e.observations);
    const ids = selected === null
      ? new Set(graph.nodes.filter(n => !nestedCalls.has(n.id)
          || n.calls > nestedCalls.get(n.id)).map(n => n.id))
      : new Set(graph.edges.filter(e => e.kind === 'contains' && e.source === selected).map(e => e.target));
    const edges = graph.edges.filter(e => ids.has(e.source) && ids.has(e.target)
      && ((e.kind === 'sequence' && e.context === selected) || e.kind === 'wait'));
    // Do not invent parent waits by lifting a descendant's dependency.
    const hiddenWaits = graph.edges.filter(e => e.kind === 'wait'
      && (ids.has(e.source) || ids.has(e.target) || e.source === selected || e.target === selected)
      && !edges.includes(e)).length;
    return {nodes:graph.nodes.filter(n => ids.has(n.id)), edges, primary:ids, hiddenWaits};
  }
  const hierarchyCache = new WeakMap();
  function hierarchy(model) {
    if (hierarchyCache.has(model)) return hierarchyCache.get(model);
    const graph=build(model), nodes=new Map(), roots=[], byCall=new Map(), stacks=new Map(), edges=new Map();
    if (graph.status!=='observed') return {nodes,roots,edges:[]};
    const add=(kind,source,target,context=null,meta={})=>{
      const key=JSON.stringify([kind,source,target,context,meta.eventStatus]);
      if(!edges.has(key)) edges.set(key,{kind,source,target,context,observations:0,...meta});
      edges.get(key).observations++;
    };
    for(const event of [...model.trace.events].sort((a,b)=>a.group.localeCompare(b.group)||a.seq-b.seq)) {
      const context=JSON.stringify([event.group,String(event.thread)]);
      if(!stacks.has(context)) stacks.set(context,{stack:[],last:null});
      const state=stacks.get(context), stack=state.stack;
      while(stack.length&&stack.at(-1).event.end<event.seq) stack.pop();
      const parent=stack.at(-1), path=parent?[...parent.node.path,event.region]:[event.region], key=JSON.stringify(path);
      if(!nodes.has(key)) {
        const node={key,id:event.region,path,parent:parent?.node.key||null,children:[],calls:0};
        nodes.set(key,node);
        (parent?parent.node.children:roots).push(key);
      }
      const node=nodes.get(key);node.calls++;
      const previous=parent?parent.last:state.last;
      if(previous) add('sequence',previous,key,parent?.node.key||null);
      if(parent) parent.last=key;else state.last=key;
      const call={node,event,last:null};stack.push(call);byCall.set(uid(event),call);
    }
    if(model.waits?.status==='observed') {
      const publications=new Map((model.waits.events||[]).map(e=>[e.id,e]));
      for(const op of model.waits.operations||[]) {
        const consumer=byCall.get(uid(op));if(!consumer)continue;
        for(const id of op.producers||[]) {
          const pub=publications.get(id),producer=pub&&byCall.get(uid(pub));
          if(producer&&consumer.node.id!==producer.node.id) add('wait',consumer.node.key,producer.node.key,consumer.node.key);
        }
      }
    }
    for(const pair of declaredPairs(model)) {
      const consumer=byCall.get(uid(pair.consumer)),producer=byCall.get(uid(pair.producer));
      if(consumer&&producer&&consumer.node.id!==producer.node.id)add('wait',consumer.node.key,producer.node.key,consumer.node.key,
        {origin:pair.origin,eventStatus:pair.eventStatus});
    }
    const result={nodes,roots,edges:[...edges.values()]};hierarchyCache.set(model,result);return result;
  }
  function nestedView(tree, selected, mode, expanded) {
    const under=(key,ancestor)=>{
      for(let n=tree.nodes.get(key);n;n=tree.nodes.get(n.parent)) if(n.key===ancestor)return true;
      return false;
    };
    const rootOf=key=>{let n=tree.nodes.get(key);while(n.parent)n=tree.nodes.get(n.parent);return n.key;};
    let roots=mode==='top'?[...tree.roots]:mode==='waits'
      ? [...new Set(tree.edges.filter(e=>e.kind==='wait').flatMap(e=>[rootOf(e.source),rootOf(e.target)]))]
      : [...tree.nodes.values()].filter(n=>n.id===selected).map(n=>n.key);
    const relevant=tree.edges.filter(e=>e.kind==='wait'&&(mode!=='region'
      ||roots.some(k=>under(e.source,k)||under(e.target,k))));
    for(const e of relevant) for(const endpoint of [e.source,e.target])
      if(!roots.some(k=>under(endpoint,k))) roots.push(rootOf(endpoint));
    roots=[...new Set(roots)].filter(k=>!roots.some(other=>other!==k&&under(k,other)));
    const visible=new Set(), visit=key=>{
      visible.add(key);if(expanded.has(key))tree.nodes.get(key).children.forEach(visit);
    };roots.forEach(visit);
    const project=key=>{for(let n=tree.nodes.get(key);n;n=tree.nodes.get(n.parent))if(visible.has(n.key))return n.key;return null;};
    const edges=tree.edges.flatMap(e=>{
      if(e.kind==='wait') {
        if(!relevant.includes(e))return [];
        const source=project(e.source),target=project(e.target);
        return source&&target?[{...e,actualSource:e.source,actualTarget:e.target,source,target}]:[];
      }
      return mode!=='waits'&&visible.has(e.source)&&visible.has(e.target)
        &&(e.context===null?roots.includes(e.source)&&roots.includes(e.target):expanded.has(e.context))?[e]:[];
    });
    return {roots,visible,edges};
  }
  function countFormula(edge) {
    const f = edge.perInvocation;
    if (!f) return null;
    const terms = f.coefficients.flatMap((c,i) => c === '0' ? [] :
      [c === '1' ? edge.states[i] : `${c}*${edge.states[i]}`]);
    if (f.constant !== '0' || !terms.length) terms.push(f.constant);
    return terms.join(' + ').replaceAll('+ -','- ');
  }
  function layout(view, selected) {
    // Follow observed sibling order where acyclic. Cycles stay explicitly drawn;
    // positioning them does not turn them into a topological schedule.
    const pending = new Set(view.nodes.filter(n => n.id !== selected).map(n => n.id));
    const levels = [[selected]];
    while (pending.size) {
      let next = [...pending].filter(id => !view.edges.some(e => e.kind === 'sequence'
        && e.target === id && e.source !== id && pending.has(e.source))).sort();
      if (!next.length) next = [[...pending].sort()[0]];
      for (let i=0;i<next.length;i+=3) levels.push(next.slice(i,i+3));
      next.forEach(id => pending.delete(id));
    }
    const width = Math.max(...levels.map(l => l.length))*390+40;
    const positions = new Map();
    levels.forEach((level,y) => level.forEach((id,x) => positions.set(id,
      {x:(width-level.length*390)/2+x*390,y:30+y*170,width:350,height:105})));
    return {positions,width,height:levels.length*170+60};
  }
  function waits(graph) {
    const edges = graph.edges.filter(e=>e.kind==='wait'&&e.source!==e.target);
    const ids = new Set(edges.flatMap(e=>[e.source,e.target]));
    return {nodes:graph.nodes.filter(n=>ids.has(n.id)),edges,primary:ids};
  }
  return {build,focus,waits,hierarchy,nestedView,countFormula,layout};
});
