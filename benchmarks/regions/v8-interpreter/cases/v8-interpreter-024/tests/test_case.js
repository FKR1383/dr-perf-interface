'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const k of ['a','b','c']){const o={x:1,[k]:2,get y(){return 3}};assertEq(o[k],2);assertEq(o.y,3);}
