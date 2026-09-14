# Evidence

The upstream issue and merged fix identify repeated regular-expression searches in the quoted cookie decoder as quadratic. The added regression workload uses a large sequence of escapes; the fix performs one substitution pass.

Primary sources:

- https://github.com/python/cpython/issues/123067
- https://github.com/python/cpython/pull/123075
