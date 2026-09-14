'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const src of ['return 1+2','let x=3;return x*2','if(true)return 7;return 0']) assert(typeof new Function(src)==='function');
