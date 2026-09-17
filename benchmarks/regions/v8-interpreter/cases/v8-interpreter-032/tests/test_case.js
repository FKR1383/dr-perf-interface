'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const parts of [['a','b'],['x','','y'],['α','β','γ']])assertEq(parts.join(''),parts.reduce((a,b)=>a+b,''));
