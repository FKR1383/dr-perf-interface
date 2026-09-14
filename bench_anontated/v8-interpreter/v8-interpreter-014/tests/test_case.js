'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [src,val] of [['let x=1;return x',1],['for(let i=0;i<3;i++){};return 3',3],['try{return 4}catch(e){}',4]]) assertEq(new Function(src)(),val);
