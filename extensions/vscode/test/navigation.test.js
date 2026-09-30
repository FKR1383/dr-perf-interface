'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const N=require('../navigation');
test('use captured source inside workspace instead of newer working source',()=>{
  assert.equal(N.sourceRoot('','/ditto','/ditto/runs/capture/source',['/ditto']),'/ditto/runs/capture/source');
  assert.equal(N.sourceRoot('src-current','/ditto','/ditto/runs/source',['/ditto']),'/ditto/src-current');
  assert.equal(N.sourceRoot('','/ditto','/elsewhere/source',['/ditto']),'/ditto');
  assert.equal(N.sourceRoot('','/ditto','/ditto-other/source',['/ditto']),'/ditto');
  assert.equal(N.sourceRoot('','/ditto',null,['/ditto']),'/ditto');
});
test('expand the graph editor without removing or rearranging groups',()=>{
  const layout={orientation:0,groups:[{size:.5},{size:.5}]};
  const expanded=N.expandedLayout(layout,2);
  assert.deepEqual(expanded.groups,[{size:.02},{size:.98}]);
  assert.equal(layout.groups[1].size,.5);
  const nested={orientation:0,groups:[{groups:[{},{}]},{}]};
  const large=N.expandedLayout(nested,2);
  assert.equal(N.leafCount(large),3);
  assert.ok(large.groups[0].groups[1].size>.98);
  assert.equal(large.orientation,0);
  assert.deepEqual(N.expandedLayout(layout,3),layout);
});
