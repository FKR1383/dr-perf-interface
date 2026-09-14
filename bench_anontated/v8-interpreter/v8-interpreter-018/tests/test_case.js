'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const src of ['var q=1','function r(){return 2}','var s=3;function t(){return s}']) assert(typeof new Function(src)==='function');
