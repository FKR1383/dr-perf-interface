'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
const f=Function('a','b','a=9; return [arguments[0],arguments[1],arguments.length]'); for(const x of [[1,2],[3,4],[5,6]]) assertEq(JSON.stringify(f(...x)),JSON.stringify([9,x[1],2]));
