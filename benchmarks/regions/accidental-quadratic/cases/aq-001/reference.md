# Evidence

The upstream fix identifies the alias-detection loop in member registration as quadratic for enumeration creation. It replaces the repeated scan with the existing value-to-member map for hashable values.

Primary sources:

- https://github.com/python/cpython/issues/89580
- https://github.com/python/cpython/pull/28907
