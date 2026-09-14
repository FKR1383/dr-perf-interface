'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const k of ['a','b','c']){const o={};Object.defineProperty(o,k,{value:k,writable:true,configurable:true});assertEq(o[k],k);}
