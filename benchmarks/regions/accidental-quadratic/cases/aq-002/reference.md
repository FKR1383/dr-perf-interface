# Evidence

The merged upstream pull request is explicitly titled “Fix quadratic-time ModuleNode.sort_types_by_inheritance”. Its diff replaces repeated insertion/search work with an adjacency map and depth-first topological ordering.

Primary sources:

- https://github.com/cython/cython/pull/5139
