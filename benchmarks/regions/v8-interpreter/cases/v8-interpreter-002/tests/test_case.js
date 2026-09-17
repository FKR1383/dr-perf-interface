'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const src of ['var da=1,db=2;da+db','function dc(){return 4};dc()','var dd=5;dd']) assert(typeof (0,eval)(src)!=='undefined','declaration batch');
