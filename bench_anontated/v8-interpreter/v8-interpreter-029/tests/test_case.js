'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [a,x,y] of [[[1,2,1],1,0],[[,2],2,1],[[NaN],NaN,-1]]) assertEq(a.indexOf(x),y);
