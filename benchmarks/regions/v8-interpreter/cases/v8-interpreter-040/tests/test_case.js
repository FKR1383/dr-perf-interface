'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const n of [20,40,80]){const o={};for(let i=0;i<n;i++)o['p'+i]=i;assertEq(o['p'+(n-1)],n-1);}
