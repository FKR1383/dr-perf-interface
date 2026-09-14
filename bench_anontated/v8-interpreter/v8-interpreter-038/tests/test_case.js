'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const o of [{a:1},Object.create(null,{x:{value:1}}),[1,2]])assert(Object.getOwnPropertyNames(o).length>=1);
