'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const n of [8,32,128]){const a=[];a[n]=n;assertEq(a.length,n+1);assertEq(a[n],n);}
