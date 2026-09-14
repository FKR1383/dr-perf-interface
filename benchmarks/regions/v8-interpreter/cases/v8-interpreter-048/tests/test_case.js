'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [o,k,y] of [[{a:1},'a',true],[Object.defineProperty({},'x',{value:1}),'x',false],[[],'0',true]])assertEq(Reflect.deleteProperty(o,k),y);
