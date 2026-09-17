'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [src,val] of [['var x=2;x',2],['function f(){return 3};f()',3],['let y=4;y',4]]) assertEq(eval(src),val);
