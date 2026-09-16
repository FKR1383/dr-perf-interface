/* Synthetic counterexamples. PCVs are computed before the SAME measured call.
 * Build and run with validate.py; unsigned arithmetic has defined wraparound. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "../../perfmark/perfmark.h"

#define NOINLINE __attribute__((noinline))
#define KEEP(x) __asm__ __volatile__("" : "+r"(x))
typedef uint64_t (*kernel)(long, long, const unsigned char *);

static NOINLINE uint64_t heavy(uint64_t x) {
    uint64_t s = 0;
    for (int i = 0; i < 32; ++i) { s += x; KEEP(s); }
    return s;
}
static NOINLINE uint64_t light(uint64_t x) { KEEP(x); return x; }

/* 1. Affine in n,m cannot describe the interaction n*m. */
static NOINLINE uint64_t product(long n, long m, const unsigned char *unused) {
    (void)unused;
    uint64_t s = 0;
    for (long i = 0; i < n; ++i)
        for (long j = 0; j < m; ++j) s += heavy((uint64_t)j + 1);
    return s;
}

/* 2. A branch in a loop saturates when y reaches x. */
static NOINLINE uint64_t clamp(long x, long y, const unsigned char *unused) {
    (void)unused;
    uint64_t s = 0;
    for (long i = 0; i < x; ++i)
        s += i < y ? heavy((uint64_t)i + 1) : light((uint64_t)i + 1);
    return s;
}

/* 3. Hidden data composition, even for equal lengths. */
static NOINLINE uint64_t data(long n, long unused, const unsigned char *mask) {
    (void)unused;
    uint64_t s = 0;
    for (long i = 0; i < n; ++i)
        s += mask[i] ? heavy((uint64_t)i + 1) : light((uint64_t)i + 1);
    return s;
}

/* 4. n is a decoy; training only on m=n hides the mistake. */
static NOINLINE uint64_t correlated(long n, long m, const unsigned char *unused) {
    (void)n; (void)unused;
    uint64_t s = 0;
    for (long i = 0; i < m; ++i) s += heavy((uint64_t)i + 1);
    return s;
}

/* 5. Small inputs never exercise the quadratic path. */
static NOINLINE uint64_t threshold(long n, long unused, const unsigned char *p) {
    (void)unused;
    if (n <= 64) return correlated(0, n, p);
    return product(n, n, p);
}

/* 6. A short, irregular branch can disappear inside per-block tolerance. */
static NOINLINE uint64_t tiny(long x, long unused, const unsigned char *p) {
    (void)unused; (void)p;
    uint64_t s = 0;
    if (x == 2)
        for (int i = 0; i < 16; ++i) { s += (uint64_t)i; KEEP(s); }
    return s;
}

static NOINLINE uint64_t measure(const char *region, kernel fn,
        int k, const char *const *names, const int64_t *values,
        long n, long m, const unsigned char *p) {
    perfmark_begin_v(region, k, names, values);
    uint64_t s = fn(n, m, p);
    perfmark_end(region);
    return s;
}

static unsigned checks;
static void check(const char *r, kernel fn, int k,
        const char *const *names, const int64_t *v,
        long n, long m, const unsigned char *p, uint64_t expected) {
    for (int rep = 0; rep < 3; ++rep) {
        assert(measure(r, fn, k, names, v, n, m, p) == expected);
        ++checks;
    }
}
static uint64_t sum_to(long n) { return (uint64_t)n * (n + 1) / 2; }

int main(void) {
    const long sizes[] = {128, 256, 512, 1024};
    const long widths[] = {16, 64, 256, 1536};
    const char *nm[] = {"n", "m"};
    const char *nmprod[] = {"n", "m", "n_times_m"};
    const char *branches[] = {"heavy_iters", "light_iters"};
    const char *nonly[] = {"n"};
    const char *monly[] = {"m"};
    unsigned char mask[1024];
    for (unsigned i = 0; i < 4; ++i) {
        long n = sizes[i];
        for (unsigned j = 0; j < 4; ++j) {
            long m = widths[j];
            int64_t v[] = {n, m, n * m};
            check("product_raw", product, 2, nm, v, n, m, NULL, 32 * n * sum_to(m));
            check("product_fixed", product, 3, nmprod, v, n, m, NULL, 32 * n * sum_to(m));
            long h = n < m ? n : m;
            int64_t b[] = {h, n - h};
            uint64_t expected = sum_to(n) + 31 * sum_to(h);
            check("clamp_raw", clamp, 2, nm, v, n, m, NULL, expected);
            check("clamp_fixed", clamp, 2, branches, b, n, m, NULL, expected);
            check("correlation_grid_raw", correlated, 1, nonly, v, n, m, NULL, 32 * sum_to(m));
            check("correlation_fixed", correlated, 1, monly, v + 1, n, m, NULL, 32 * sum_to(m));
        }
        int64_t v[] = {n, n};
        check("correlation_train", correlated, 1, nonly, v, n, n, NULL, 32 * sum_to(n));
        check("correlation_train_dependent", correlated, 2, nm, v, n, n, NULL, 32 * sum_to(n));
        for (int mode = 0; mode < 3; ++mode) {
            long h = mode * n / 2;
            uint64_t expected = 0;
            /* Producer already knows h. A consumer without this metadata
             * would have to scan the mask to construct the same PCV. */
            for (long j = 0; j < n; ++j) {
                mask[j] = j < h;
                expected += (uint64_t)(j + 1) * (mask[j] ? 32 : 1);
            }
            int64_t b[] = {h, n - h};
            check("data_averaged", data, 1, nonly, v, n, 0, mask, expected);
            check("data_fixed", data, 2, branches, b, n, 0, mask, expected);
            if (mode != 1)
                check(mode == 0 ? "data_light" : "data_heavy", data, 1, nonly, v, n, 0, mask, expected);
        }
    }
    const long ns[] = {8, 16, 32, 48, 64, 96, 128, 192, 256};
    const char *gated[] = {"small_n", "large_n", "large_n_squared", "large_path"};
    for (unsigned i = 0; i < 9; ++i) {
        long n = ns[i];
        int64_t v[] = {n};
        int64_t b[] = {n <= 64 ? n : 0, n > 64 ? n : 0, n > 64 ? n*n : 0, n > 64};
        uint64_t expected = 32 * sum_to(n) * (n <= 64 ? 1 : n);
        check(i < 5 ? "threshold_train" : "threshold_holdout", threshold, 1, nonly, v, n, 0, NULL, expected);
        check("threshold_all_raw", threshold, 1, nonly, v, n, 0, NULL, expected);
        check("threshold_fixed", threshold, 4, gated, b, n, 0, NULL, expected);
    }
    const char *tiny_names[] = {"x", "takes_branch"};
    for (long x = 0; x < 5; ++x) {
        int64_t v[] = {x, x == 2};
        check("tolerance_raw", tiny, 1, tiny_names, v, x, 0, NULL, x == 2 ? 120 : 0);
        check("tolerance_fixed", tiny, 2, tiny_names, v, x, 0, NULL, x == 2 ? 120 : 0);
    }
    printf("PASS: %u measured calls checked against independent result oracles\n", checks);
    return 0;
}
