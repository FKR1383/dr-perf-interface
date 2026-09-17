'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
const f=new Function('x','if(x<0)return -1;if(x===0)return 0;return 1');for(const [x,y] of [[-2,-1],[0,0],[3,1]])assertEq(f(x),y);
