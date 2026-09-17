'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [s,a,b,w] of [['aba','a','x','xba'],['ccc','c','z','zcc'],['xyz','q','p','xyz']])assertEq(s.replace(a,b),w);
