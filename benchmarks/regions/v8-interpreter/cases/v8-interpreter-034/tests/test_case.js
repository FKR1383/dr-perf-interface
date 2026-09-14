'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [a,b] of [['a','b'],['same','same'],['β','α']]){assertEq(Math.sign(a.localeCompare(b)),Math.sign(a===b?0:a<b?-1:1));}
