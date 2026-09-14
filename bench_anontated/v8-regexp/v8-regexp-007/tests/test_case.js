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

const r = /((a)(b))(?:c)(d)/; assertEq(r.exec("abcd").slice(1).join("|"), "ab|a|b|d", "capture layout"); assertEq(r.test("abce"), false, "capture mismatch");
