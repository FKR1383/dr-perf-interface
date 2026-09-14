'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [a,x,y] of [[[1,2,3],2,true],[[,],undefined,true],[[NaN],NaN,true]]) assertEq(a.includes(x),y);
