'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const o of [new Proxy({a:1},{ownKeys:t=>Reflect.ownKeys(t)}),Object.assign(Object.create(null),{b:2}),{c:3}])assertEq(Object.entries(o).length,1);
