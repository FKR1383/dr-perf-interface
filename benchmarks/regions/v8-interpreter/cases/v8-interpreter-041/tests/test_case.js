'use strict';
function assert(value, message) { if (!value) throw new Error(message || 'assertion failed'); }
function assertEq(actual, expected, message) { if (!Object.is(actual, expected)) throw new Error((message || 'values differ') + ': ' + actual + ' !== ' + expected); }
for(const v of [1,2,3]){class C{#x;constructor(x){this.#x=x}get(){return this.#x}}assertEq(new C(v).get(),v);}
