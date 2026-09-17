'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const x of [0,1,2]){let y;try{if(x===1)throw x;y=x}catch(e){y=e+2}assertEq(y,x===1?3:x);}
