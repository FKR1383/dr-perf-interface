'use strict';
const path = require('node:path');

function sourceRoot(configured, workspaceRoot, recordedRoot, workspaceRoots = []) {
  if (configured) return path.resolve(workspaceRoot || '', configured);
  // A portable report may point to a captured source tree. Automatically use
  // it only inside an open workspace; external trees require explicit config.
  if (typeof recordedRoot === 'string' && path.isAbsolute(recordedRoot)
      && workspaceRoots.some(root => {
        const relative = path.relative(root, recordedRoot);
        return relative !== '..' && !relative.startsWith('..'+path.sep) && !path.isAbsolute(relative);
      })) return recordedRoot;
  return workspaceRoot;
}

function leafCount(layout) {
  return layout.groups ? layout.groups.reduce((n,g) => n+leafCount(g),0) : 1;
}
function expandedLayout(layout, column) {
  const total = leafCount(layout);
  if (total < 2 || column < 1 || column > total) return layout;
  const copy = structuredClone(layout);
  let index = 0;
  function weight(node) {
    if (!node.groups) return ++index === column ? .98 : .02/(total-1);
    const weights = node.groups.map(weight), sum = weights.reduce((a,b)=>a+b,0);
    node.groups.forEach((g,i)=>{g.size=weights[i]/sum;});
    return sum;
  }
  weight(copy);
  return copy;
}
module.exports = {sourceRoot,leafCount,expandedLayout};
