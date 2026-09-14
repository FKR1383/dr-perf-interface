'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const [o,k,y] of [[{a:1},'a',true],[Object.create({a:1}),'a',false],[[,],'0',false]])assertEq(Object.hasOwn(o,k),y);
