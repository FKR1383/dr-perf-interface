# Evidence

The merged upstream pull request is explicitly titled “Fix quadratic time look up in find_files”. It changes duplicate tracking from a list to a set, eliminating a growing linear membership scan for every glob result.

Primary sources:

- https://github.com/SocketDev/socket-python-cli/pull/22
