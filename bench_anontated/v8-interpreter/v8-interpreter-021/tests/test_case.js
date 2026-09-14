'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const o of [{a:1},{a:1,b:2},Object.assign(Object.create({z:9}),{c:3})]){let n=0;for(const k in o){assert(typeof k==='string');n++}assert(n>=1);}
