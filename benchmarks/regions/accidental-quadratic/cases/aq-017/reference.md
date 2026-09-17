# Evidence

The upstream security issue explicitly lists get_section or the corresponding vulnerable source line in email._header_value_parser among quadratic-complexity locations. The later upstream parser fix tracks this issue and removes non-linear parsing behavior.

Primary sources:

- https://github.com/python/cpython/issues/136063
- https://github.com/python/cpython/pull/152521
