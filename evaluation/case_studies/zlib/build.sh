#!/bin/sh
set -eu
cd "$(dirname "$0")"
"${CC:-cc}" -O2 -g -std=c99 -Wall -Wextra -I zlib \
    driver.c zlib/adler32.c zlib/crc32.c zlib/deflate.c zlib/trees.c \
    zlib/zutil.c zlib/inflate.c zlib/inftrees.c zlib/inffast.c zlib/uncompr.c \
    -L. -lperfmark '-Wl,-rpath,$ORIGIN' -o program
