#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Preserve the upstream GNU89 inline semantics; no OpenMP runtime is used.
"${CC:-cc}" -O2 -g -std=gnu89 -Irodinia -c rodinia/kmeans_clustering.c -o kmeans.o
"${CC:-cc}" -O2 -g -std=c99 -Wall -Wextra -I. \
    driver.c kmeans.o -L. -lperfmark -lm '-Wl,-rpath,$ORIGIN' -o program
