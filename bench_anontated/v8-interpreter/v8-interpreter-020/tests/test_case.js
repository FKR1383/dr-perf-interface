'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const n of [1,4,7]){let s=0;for(let i=0;i<n;i++){if(i===5)break;if(i%2)continue;s+=i}assert(s>=0);}
