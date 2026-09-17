'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
function outer(){return (function(){return arguments.length+arguments[0]})(...arguments)} for(const a of [[1],[2,3],[4,5,6]]) assertEq(outer(...a),a.length+a[0]);
