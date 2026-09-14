'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const s of ['a\"b',"a'b",'a\\b']){const q=JSON.stringify(s);assertEq(JSON.parse(q),s);}
