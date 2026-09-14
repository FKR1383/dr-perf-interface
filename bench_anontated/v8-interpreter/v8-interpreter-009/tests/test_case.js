'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const k of ['a','b','c']){const o={[k]:1};const f=Function('o',`with(o){return delete ${k}}`);assertEq(f(o),true);assertEq(k in o,false);}
