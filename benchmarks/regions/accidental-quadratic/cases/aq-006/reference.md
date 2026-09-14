# Evidence

The upstream security issue names posixpath.expandvars as a quadratic-complexity location. The merged fix replaces repeated prefix reconstruction with one regular-expression substitution pass and adds a large regression workload.

Primary sources:

- https://github.com/python/cpython/issues/136065
- https://github.com/python/cpython/pull/134952
