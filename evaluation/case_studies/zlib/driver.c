#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "zlib.h"
#include "perfmark/perfmark.h"

static void fail(const char *message)
{
    fprintf(stderr, "%s\n", message);
    exit(1);
}

__attribute__((noinline))
static unsigned long compress_buffer(const unsigned char *input, size_t n, int level)
{
    z_stream strm = {0};
    if (deflateInit(&strm, level) != Z_OK)
        fail("deflateInit failed");
    uLong capacity = deflateBound(&strm, (uLong)n);
    if (n > UINT_MAX || capacity > UINT_MAX)
        fail("input too large for this driver");
    unsigned char *output = malloc(capacity);
    unsigned char *decoded = malloc(n);
    if (!output || !decoded)
        fail("allocation failed");
    strm.next_in = (Bytef *)input;
    strm.avail_in = (uInt)n;
    strm.next_out = output;
    strm.avail_out = (uInt)capacity;
    int status;

    /* EVALUATION_STATES_BEGIN */
    perfmark_begin("compress", "n", (int64_t)n);
    /* EVALUATION_STATES_END */
    do {
        status = deflate(&strm, Z_FINISH);
    } while (status == Z_OK && strm.avail_out != 0);
    perfmark_end("compress");

    if (status != Z_STREAM_END || strm.avail_in != 0)
        fail("compression did not finish");
    unsigned long compressed = strm.total_out;
    uLongf decoded_size = (uLongf)n;
    if (uncompress(decoded, &decoded_size, output, compressed) != Z_OK ||
        decoded_size != n || memcmp(input, decoded, n) != 0)
        fail("decompression did not reproduce the input");
    if (deflateEnd(&strm) != Z_OK)
        fail("deflateEnd failed");
    free(decoded);
    free(output);
    return compressed;
}

int main(int argc, char **argv)
{
    if (argc != 2)
        fail("usage: ./program workloads/discovery.tsv");
    FILE *manifest = fopen(argv[1], "r");
    if (!manifest)
        fail("cannot open workload manifest");
    char row[1024], path[512], extra;
    size_t n;
    int level;
    unsigned cases = 0;
    uint64_t input_bytes = 0, output_bytes = 0;
    while (fgets(row, sizeof(row), manifest)) {
        if (row[0] == '#' || row[0] == '\n')
            continue;
        if (sscanf(row, "%511s %zu %d %c", path, &n, &level, &extra) != 3 ||
            n == 0 || n > 1024 * 1024 || level < 1 || level > 9)
            fail("invalid workload row");
        FILE *file = fopen(path, "rb");
        if (!file)
            fail("cannot open input file");
        unsigned char *input = malloc(n);
        if (!input || fread(input, 1, n, file) != n)
            fail("cannot read requested input bytes");
        fclose(file);
        output_bytes += compress_buffer(input, n, level);
        input_bytes += n;
        cases++;
        free(input);
    }
    if (ferror(manifest) || cases == 0)
        fail("empty or unreadable workload");
    fclose(manifest);
    printf("verified %u cases; input_bytes=%" PRIu64 "; compressed_bytes=%" PRIu64 "\n",
           cases, input_bytes, output_bytes);
    return 0;
}
