'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const L=require('../media/graph-layout');
const node=(children=[])=>({width:260,header:64,children});
const overlap=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
test('ELK keeps disconnected regions in horizontal input order without overlap',async()=>{
  const nodes=new Map(Array.from({length:11},(_,i)=>['n'+i,node()]));
  const g=await L.layout([...nodes.keys()],nodes,[{source:'n0',target:'n1'}]);
  const boxes=[...g.boxes.values()];
  assert.equal(boxes.length,11);
  assert.ok(boxes.every((b,i)=>i===0||b.x>=boxes[i-1].x+boxes[i-1].width));
  assert.equal(new Set(boxes.map(b=>b.y)).size,1);
  assert.equal(g.routes.size,1,'ordering constraints are not exposed as relationships');
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++)assert.equal(overlap(boxes[i],boxes[j]),false);
  assert.ok(g.routes.get(0)?.[0].length>=2);
});
test('ELK preserves nested containment and routes across compound regions',async()=>{
  const nodes=new Map([['a',node(['b','c'])],['b',node()],['c',node()],['d',node(['e'])],['e',node()]]);
  const edges=[{source:'b',target:'e'},{source:'c',target:'b'}];
  const g=await L.layout(['a','d'],nodes,edges);
  for(const [parent,child]of [['a','b'],['a','c'],['d','e']]){
    const p=g.boxes.get(parent),c=g.boxes.get(child);
    assert.ok(c.x>=p.x&&c.y>=p.y+64&&c.x+c.width<=p.x+p.width&&c.y+c.height<=p.y+p.height);
  }
  for(let i=0;i<edges.length;i++)assert.ok(g.routes.get(i)?.[0].length>=2);
  assert.equal(overlap(g.boxes.get('a'),g.boxes.get('d')),false);
  assert.equal(overlap(g.boxes.get('b'),g.boxes.get('c')),false);
});
test('ELK can route from a parent to its child and handle an empty wait view',async()=>{
  const nodes=new Map([['a',node(['b'])],['b',node()]]);
  const g=await L.layout(['a'],nodes,[{source:'a',target:'b'}]);
  assert.ok(g.routes.get(0)?.[0].length>=2);
  const empty=await L.layout([],new Map(),[]);
  assert.equal(empty.boxes.size,0);
});

test('expansion keeps root order and stacks children vertically',async()=>{
  const nodes=new Map([['a',node()],['b',node()],['c',node()],['d',node()],['e',node()]]);
  const before=await L.layout(['a','b','e'],nodes,[]);
  nodes.get('b').children=['c','d'];
  const after=await L.layout(['a','b','e'],nodes,[]);
  assert.equal(after.boxes.get('a').x,before.boxes.get('a').x);
  assert.equal(after.boxes.get('b').x,before.boxes.get('b').x);
  assert.ok(after.boxes.get('e').x>before.boxes.get('e').x);
  assert.equal(after.boxes.get('d').x,after.boxes.get('c').x);
  assert.ok(after.boxes.get('d').y>=after.boxes.get('c').y+after.boxes.get('c').height);
  assert.equal(after.routes.size,0);
});

test('deep vertical containers keep routed waits connected across boundaries',async()=>{
  const nodes=new Map([['a',node(['b','c'])],['b',node(['d','e'])],['c',node()],
    ['d',node()],['e',node()],['f',node(['g','h'])],['g',node()],['h',node()]]);
  const edges=[{source:'d',target:'g'},{source:'h',target:'e'},
    {source:'a',target:'e'},{source:'e',target:'a'},{source:'e',target:'d'}];
  const g=await L.layout(['a','f'],nodes,edges);
  for(const [upper,lower]of [['b','c'],['d','e'],['g','h']]){
    const a=g.boxes.get(upper),b=g.boxes.get(lower);
    assert.ok(b.y>=a.y+a.height,'children stack vertically');
  }
  const onBoundary=(p,b)=>p.x>=b.x-.01&&p.x<=b.x+b.width+.01&&p.y>=b.y-.01&&p.y<=b.y+b.height+.01&&
    [p.x-b.x,p.x-b.x-b.width,p.y-b.y,p.y-b.y-b.height].some(d=>Math.abs(d)<.01);
  for(const [i,e]of edges.entries()){
    const [path]=g.routes.get(i);
    assert.ok(onBoundary(path[0],g.boxes.get(e.source)),'wait starts at the actual source');
    assert.ok(onBoundary(path.at(-1),g.boxes.get(e.target)),'wait ends at the actual target');
    for(let j=1;j<path.length;j++)assert.ok(Math.abs(path[j].x-path[j-1].x)<.01||Math.abs(path[j].y-path[j-1].y)<.01,
      'boundary segments join without diagonal jumps');
  }
});
