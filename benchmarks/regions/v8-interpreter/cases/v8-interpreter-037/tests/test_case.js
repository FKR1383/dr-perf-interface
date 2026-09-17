'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const o of [{a:1},{2:1,a:2},Object.defineProperty({a:1},'x',{value:2})])assert(Array.isArray(Object.keys(o)));
