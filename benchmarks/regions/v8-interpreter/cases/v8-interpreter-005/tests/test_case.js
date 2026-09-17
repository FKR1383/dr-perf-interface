'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
const exercise = new Function('log', 'fail', "{ using x = { [Symbol.dispose]() { log.push('d') } }; if (fail) throw new Error('expected'); }");
for (const fail of [false, true]) {
  const log = [];
  let threw = false;
  try { exercise(log, fail); }
  catch (error) { threw = true; assertEq(error.message, 'expected'); }
  assertEq(threw, fail);
  assertEq(log.join(','), 'd');
}
