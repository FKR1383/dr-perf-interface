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

check(/(Ä+)-\1/iu, [["Ä-ä", true], ["ää-ÄÄ", true], ["Ä-ö", false], ["ÄÄ-ää", true]]);
