/* Exercise key contents, cached keys, and both small/dynamic PCV paths. */
#include <stdint.h>
#include <stdio.h>
#include "../perfmark/perfmark.h"

int main(void) {
    const int counts[] = {0, 1, 4, 6, 8, 9, 16, 64};
    char labels[64][32], region[32];
    const char *names[64];
    int64_t values[64];
    for (int j = 0; j < 64; ++j) {
        snprintf(labels[j], sizeof(labels[j]), "pcv_%d", j);
        names[j] = labels[j];
    }
    for (unsigned c = 0; c < sizeof(counts)/sizeof(counts[0]); ++c) {
        int n = counts[c];
        snprintf(region, sizeof(region), "pcvs_%d", n);
        for (int repeat = 0; repeat < 2; ++repeat)
            for (int variant = 0; variant < 3; ++variant) {
                for (int j = 0; j < n; ++j)
                    values[j] = (INT64_C(1) << 54) + j + (j == n-1 ? variant : 0);
                perfmark_begin_v(region, n, names, values);
                __asm__ __volatile__("" ::: "memory");
                perfmark_end(region);
            }
    }
    puts("PASS: C markers with 0..64 PCVs");
    return 0;
}
