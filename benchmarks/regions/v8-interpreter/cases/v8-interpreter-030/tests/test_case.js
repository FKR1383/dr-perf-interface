'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
assertEq('abc'.replace(/(b)/,'[$1]'),'a[b]c');assertEq('abc'.replace('b','$&$&'),'abbc');assertEq('abc'.replace('b','$`'),'aac');
