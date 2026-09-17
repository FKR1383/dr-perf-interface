# Evidence

The merged upstream fix states that the lazy quoted-field regular expression scans to the end of the sample from every candidate start, producing quadratic time. Its regression uses 10,000 quoted records.

Primary sources:

- https://github.com/python/cpython/issues/98820
- https://github.com/python/cpython/pull/154867
