'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const G=require('../media/execution-graph');

function fixture() {
  const events=[];let seq=0;
  function call(region,body,thread='1',group='0:1') {
    const e={region,values:{},group,thread,seq:++seq};events.push(e);
    if(body)body();e.end=++seq;return e;
  }
  function model() {
    return {validity:{errors:[],traceErrors:[]},trace:{complete:true,events},
      regions:[...new Set(events.map(e=>e.region))].map(id=>{
        const calls=events.filter(e=>e.region===id).length;
        return {id,states:[],calls,points:[{state:[],calls}]};
      })};
  }
  return {call,model};
}
const keys=g=>g.edges.map(e=>[e.kind,e.source,e.target,e.context,e.observations]);
test('all waits exposes global dependencies outside selected neighborhood',()=>{
  const graph={nodes:['a','b','c','d'].map(id=>({id})),edges:[
    {kind:'contains',source:'a',target:'b'},
    {kind:'wait',source:'c',target:'d'},
    {kind:'wait',source:'d',target:'d'}]};
  assert.equal(G.focus(graph,'a').edges.some(e=>e.kind==='wait'),false);
  const view=G.waits(graph);
  assert.deepEqual(view.nodes.map(n=>n.id),['c','d']);
  assert.equal(view.edges.length,1);
});
test('direct siblings, nesting and repeated calls remain distinct',()=>{
  const f=fixture();f.call('p',()=>{f.call('a');f.call('b');f.call('b');});
  assert.deepEqual(keys(G.build(f.model())),[
    ['contains','p','a','p',1],['contains','p','b','p',2],
    ['sequence','a','b','p',1],['sequence','b','b','p',1]]);
});
test('never orders independent processes or execution contexts',()=>{
  const f=fixture();f.call('a');f.call('other',null,'2');f.call('elsewhere',null,'1','1:2');f.call('b');
  assert.deepEqual(keys(G.build(f.model())),[['sequence','a','b',null,1]]);
});
test('incomplete, crossing and counter-mismatched traces are unavailable',()=>{
  for(const kind of ['partial','crossing','counter','error']) {
    const f=fixture();f.call('p',()=>f.call('c'));const m=f.model();
    if(kind==='partial')m.trace.complete=false;
    if(kind==='crossing')m.trace.events[1].end=9;
    if(kind==='counter')m.regions[0].points[0].calls++;
    if(kind==='error')m.validity.errors.push('overflow');
    assert.equal(G.build(m).status,'unavailable',kind);
  }
});
test('wait links require captured producer evidence, not temporal proximity',()=>{
  const f=fixture(),pub=f.call('producer'),op=f.call('consumer',null,'2'),m=f.model();
  m.waits={status:'observed',events:[{...pub,id:'publication'}],
    operations:[{...op,api:'sem_wait',producers:['publication']}]};
  const g=G.build(m);assert.deepEqual(keys(g),[['wait','consumer','producer','consumer',1]]);
  assert.equal(g.nodes.length,2);
  for(const condition of ['partial','missing']) {
    const copy=structuredClone(m);
    if(condition==='partial')copy.waits.status='partial';else copy.waits.events=[];
    const x=G.build(copy);assert.equal(x.edges.length,0);
    assert.equal(x.nodes.find(n=>n.id==='consumer').waitOperations['<unresolved>'],1);
  }
});
test('focus is one level without containment edges or external endpoints',()=>{
  const f=fixture();f.call('p',()=>f.call('c',()=>f.call('g')));f.call('x',null,'2');
  const graph=G.build(f.model());graph.edges.push({kind:'wait',source:'c',target:'x',observations:1});
  const v=G.focus(graph,'p');assert.deepEqual(v.nodes.map(n=>n.id),['c']);
  const l=G.layout(v,'c');assert.equal(l.positions.size,1);
  assert.ok(l.width>0&&l.height>0);
});
test('sequence cycles and self waits produce a finite layout',()=>{
  const f=fixture();f.call('p',()=>{f.call('a');f.call('b');f.call('a');});
  const v=G.focus(G.build(f.model()),'p');assert.equal(G.layout(v,'a').positions.size,2);
});
test('portable graphs preserve exact count formulas and reject corrupt endpoints',()=>{
  const f=fixture();f.call('p',()=>f.call('c'));const m=f.model();
  const g=G.build(m);m.executionGraph=structuredClone(g);
  m.executionGraph.edges[0].perInvocation={coefficients:[],constant:'1'};
  m.executionGraph.edges[0].states=[];
  const fresh=structuredClone(m);assert.equal(G.countFormula(G.build(fresh).edges[0]),'1');
  fresh.executionGraph.edges[0].target='missing';
  assert.equal(G.build(structuredClone(fresh)).status,'unavailable');
  assert.equal(G.countFormula({states:['pages'],perInvocation:{coefficients:['1/8'],constant:'0'}}),'1/8*pages');
});

test('nested waits retain actual endpoints and independent expansion',()=>{
  const f=fixture();let consumer,producer;
  f.call('A',()=>{consumer=f.call('a1');});
  f.call('B',()=>{producer=f.call('b1');});
  const m=f.model();m.waits={status:'observed',events:[{...producer,id:'pub'}],
    operations:[{...consumer,producers:['pub']}]};
  const h=G.hierarchy(m),A=JSON.stringify(['A']),B=JSON.stringify(['B']);
  const expanded=new Set(),collapsed=G.nestedView(h,'A','top',expanded);
  const edge=collapsed.edges.find(e=>e.kind==='wait');
  assert.equal(edge.source,A);assert.equal(edge.target,B);
  assert.equal(h.nodes.get(edge.actualSource).id,'a1');
  expanded.add(A);const half=G.nestedView(h,'A','top',expanded).edges.find(e=>e.kind==='wait');
  assert.equal(half.source,JSON.stringify(['A','a1']));assert.equal(half.target,B);
  expanded.add(B);const full=G.nestedView(h,'A','top',expanded).edges.find(e=>e.kind==='wait');
  assert.equal(full.target,JSON.stringify(['B','b1']));
});
test('same region name in different parents does not misattribute a wait',()=>{
  const f=fixture();let consumer,producer;
  f.call('A',()=>f.call('shared'));
  f.call('B',()=>{consumer=f.call('shared');producer=f.call('producer');});
  const m=f.model();m.waits={status:'observed',events:[{...producer,id:'pub'}],operations:[{...consumer,producers:['pub']}]};
  const tree=G.hierarchy(m),view=G.nestedView(tree,'A','region',new Set());
  assert.equal(view.edges.filter(e=>e.kind==='wait').length,0);
  const all=G.nestedView(tree,'A','waits',new Set());
  assert.deepEqual(all.roots,[JSON.stringify(['B'])]);
  const wait=all.edges.find(e=>e.kind==='wait');assert.equal(wait.source,wait.target);
});

test('declared waits preserve status, nested endpoints and older exported graphs',()=>{
  const f=fixture();let producer,consumer;
  f.call('P',()=>{producer=f.call('build');},'1');
  f.call('C',()=>{consumer=f.call('get',null,'2');},'2');
  const m=f.model();
  const old=structuredClone(G.build(m));
  m.waits={status:'observed',events:[{...producer,id:'publish'}, {...consumer,id:'waited'}],operations:[]};
  m.eventModel={status:'violation',probe:true,violations:[{}],edges:
    ['ordered','violation'].map(status=>({waited:'waited',publication:'publish',status}))};
  for(const exported of [null,old]){
    const copy=structuredClone(m);
    if(exported)copy.executionGraph=exported;
    const g=G.build(copy),waits=g.edges.filter(e=>e.kind==='wait');
    assert.deepEqual(waits.map(e=>e.eventStatus),['ordered','violation']);
    assert.equal(g.eventChecks.violations,1);assert.equal(g.eventChecks.probe,true);
    const tree=G.hierarchy(copy),view=G.nestedView(tree,'C','top',new Set());
    const edges=view.edges.filter(e=>e.kind==='wait');assert.equal(edges.length,2);
    for(const e of edges){
      assert.equal(tree.nodes.get(e.actualSource).id,'get');
      assert.equal(tree.nodes.get(e.actualTarget).id,'build');
      assert.equal(tree.nodes.get(e.source).id,'C');
      assert.equal(tree.nodes.get(e.target).id,'P');
    }
    copy.executionGraph={...structuredClone(g),declaredEventsIncluded:true};
    assert.equal(G.waits(G.build(structuredClone(copy))).edges.length,2);
  }
  const missing=structuredClone(m);missing.waits.events.pop();
  assert.equal(G.waits(G.build(missing)).edges.length,0);
  const partial=structuredClone(m);partial.waits.status='partial';
  assert.equal(G.waits(G.build(partial)).edges.length,0);
});

test('same-region native and declared waits remain evidence, not graph edges',()=>{
  const f=fixture(),pub=f.call('same'),op=f.call('same',null,'2'),m=f.model();
  m.waits={status:'observed',events:[{...pub,id:'publication'},{...op,id:'waited'}],
    operations:[{...op,id:'waited',api:'sem_wait',producers:['publication']}]};
  m.eventModel={edges:[{publication:'publication',waited:'waited',status:'ordered',event:'1',generation:'1'}]};
  const g=G.build(m);
  assert.equal(g.edges.filter(e=>e.kind==='wait').length,0);
  assert.equal(g.nodes[0].waitOperations.sem_wait,1);
  assert.equal(g.nodes[0].waitOperations['<unresolved>'],undefined);
  assert.equal(G.hierarchy(m).edges.filter(e=>e.kind==='wait').length,0);
  m.executionGraph={...g,declaredEventsIncluded:true,edges:[{kind:'wait',source:'same',target:'same',context:'same',observations:1}]};
  const exported=G.build(structuredClone(m));
  assert.equal(exported.status,'observed');
  assert.equal(exported.edges.length,0);
  assert.equal(m.waits.operations.length,1);
});
