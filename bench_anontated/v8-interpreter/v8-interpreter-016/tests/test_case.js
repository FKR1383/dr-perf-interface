'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
(async()=>{for(const v of [1,2,3]) assertEq(await (async x=>await Promise.resolve(x+1))(v),v+1);})().catch(e=>{throw e});
