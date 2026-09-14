'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
const s=Symbol('s');for(const [o,n] of [[{a:1,2:3},2],[{[s]:1},1],[Object.defineProperty({},'x',{value:1}),1]])assertEq(Reflect.ownKeys(o).length,n);
