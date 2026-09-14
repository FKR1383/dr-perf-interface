# Evidence

The upstream security fix is explicitly titled “Fix quadratic complexity in processing special input in HTMLParser”. Its regression test lists incomplete start tags, declarations, comments, and processing instructions that previously took about an hour at bounded large sizes.

Primary sources:

- https://github.com/python/cpython/issues/135462
- https://github.com/python/cpython/pull/135464
