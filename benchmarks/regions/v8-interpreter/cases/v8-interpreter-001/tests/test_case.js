'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for (const [src,key,val] of [['var ga=1;ga','ga',1],['function gb(){return 2};gb()','gb',2],['var gc;gc=3;gc','gc',3]]) assertEq((0,eval)(src),val,key);
