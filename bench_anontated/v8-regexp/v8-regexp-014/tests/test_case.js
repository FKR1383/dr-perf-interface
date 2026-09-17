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

let supported = true; let r; try { r = new RegExp("^[\\q{cat|dog}]+$", "v"); } catch (_) { supported = false; } if (supported) check(r, [["cat", true], ["dogcat", true], ["cow", false], ["dog", true]]); else throw new Error("This test requires Unicode Sets (v flag); use the pinned d8 build.");
