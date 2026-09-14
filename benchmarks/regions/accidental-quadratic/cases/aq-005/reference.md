# Evidence

The upstream security issue names ntpath.expandvars as a quadratic-complexity location. The merged fix removes repeated slicing and concatenation and adds a 100,000-token regression workload.

Primary sources:

- https://github.com/python/cpython/issues/136065
- https://github.com/python/cpython/pull/134952
