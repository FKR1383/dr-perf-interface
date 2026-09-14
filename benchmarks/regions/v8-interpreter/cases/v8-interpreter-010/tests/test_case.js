'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
const f=Function('o','with(o){return a+b}'); for(const o of [{a:1,b:2},{a:3,b:4},{a:-1,b:8}]) assertEq(f(o),o.a+o.b);
