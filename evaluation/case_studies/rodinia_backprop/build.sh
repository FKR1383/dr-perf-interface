#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Rodinia uses K&R declarations; compile its source in its original C dialect.
"${CC:-cc}" -O2 -g -std=gnu89 -include unistd.h -include fcntl.h \
    -Irodinia -c rodinia/backprop.c -o backprop.o
"${CC:-cc}" -O2 -g -std=c99 -Wall -Wextra -I. \
    driver.c backprop.o -L. -lperfmark -lm '-Wl,-rpath,$ORIGIN' -o program
