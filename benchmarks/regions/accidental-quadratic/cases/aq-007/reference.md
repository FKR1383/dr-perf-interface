# Evidence

The upstream issue lists email.message._parseparam, and the merged pull request explicitly fixes its quadratic parsing. Its regression test uses 100,000 parameters and a long unterminated quoted parameter.

Primary sources:

- https://github.com/python/cpython/issues/136063
- https://github.com/python/cpython/pull/136072
