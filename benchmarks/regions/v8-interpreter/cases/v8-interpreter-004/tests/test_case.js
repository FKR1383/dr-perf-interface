'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for (const tag of ['a', 'b', 'c']) {
  const log = [];
  new Function('log', 'tag', "{ using x = { [Symbol.dispose]() { log.push(tag) } }; }")(log, tag);
  assertEq(log.join(','), tag);
}
