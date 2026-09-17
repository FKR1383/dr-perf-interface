# Evidence

The merged upstream pull request is explicitly titled “avoid quadratic child rescan in normalize_invisible_parens”. It passes the already-known child index into the wrapping helper rather than making the helper rescan siblings.

Primary sources:

- https://github.com/psf/black/pull/5322
