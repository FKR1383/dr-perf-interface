'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const v of [1,2,3]){class A{constructor(x){this.x=x}}class B extends A{constructor(x){super(x);this.y=x+1}}const b=new B(v);assertEq(b.x+b.y,2*v+1);}
