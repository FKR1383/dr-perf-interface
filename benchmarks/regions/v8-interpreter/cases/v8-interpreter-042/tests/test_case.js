'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const p of [null,{x:1},Array.prototype]){const o=Object.create(p,{a:{value:2,enumerable:true}});assertEq(o.a,2);assertEq(Object.getPrototypeOf(o),p);}
