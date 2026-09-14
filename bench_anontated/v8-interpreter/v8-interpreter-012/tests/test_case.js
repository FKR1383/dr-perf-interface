'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [src,val] of [["return {a:1,b:'x'}.a",1],["return [1,2,3][2]",3],["return `a${2}b`",'a2b']]) assertEq(new Function(src)(),val);
