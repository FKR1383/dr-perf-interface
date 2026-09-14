'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [src,val] of [['var x=1;return x',1],['let y=2;return y',2],['const z=3;return z',3]]) assertEq(new Function(src)(),val);
