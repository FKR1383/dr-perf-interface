'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [o,k,v] of [[{},'a',1],[new Proxy({},{}),'b',2],[[],'0',3]]){assert(Reflect.set(o,k,v));assertEq(o[k],v);}
