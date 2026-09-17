"use strict";

function assertEq(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(label + ": expected " + expected + ", got " + actual);
  }
}

function check(re, samples) {
  for (const [input, expected] of samples) {
    re.lastIndex = 0;
    assertEq(re.test(input), expected, re + " on " + JSON.stringify(input));
  }
}

const r = /(?<word>[a-z]+)-(?<digit>[0-9])/; const m = r.exec("name-7"); assertEq(m.groups.word, "name", "word group"); assertEq(m.groups.digit, "7", "digit group"); assertEq(r.test("name-x"), false, "named group mismatch");
