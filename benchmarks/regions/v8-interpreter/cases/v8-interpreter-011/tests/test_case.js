'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
const f=Function('o','v','with(o){x=v} return o.x'); for(const v of [1,7,-2]) assertEq(f({x:0},v),v);
