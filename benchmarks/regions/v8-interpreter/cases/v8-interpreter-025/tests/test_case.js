'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const a of [[1,,3],[...[1,2],3],[1,...[2,3]]]){assertEq(a.length,3);assertEq(a[0],1);}
