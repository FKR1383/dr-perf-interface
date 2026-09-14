'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
assert(typeof ''.toWellFormed === 'function', 'requires String.prototype.toWellFormed in the pinned d8 build');
assertEq('abc'.toWellFormed(), 'abc');
assertEq('a\uD800b'.toWellFormed(), 'a\uFFFDb');
assertEq('\uD83D\uDE00'.toWellFormed(), '😀');
