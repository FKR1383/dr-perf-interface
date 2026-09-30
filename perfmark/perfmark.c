/* Empty marker bodies. Must be a shared library so calls go through the PLT
 * and can be wrapped by the drperf client (dr_get_proc_address on export). */
#include "perfmark.h"
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#define EXPORT __attribute__((visibility("default"), noinline))

/* Late attach: with DRPERF_LATE set, the first region starts DynamoRIO instead
 * of running the whole process under it.  Everything before the first marker
 * (imports, model loading, warm-up) runs natively.  After attaching, the call
 * is made again through the PLT so the client, which is now running, sees the
 * region open. */
static int attach_state;        /* 0 unchecked, 1 attaching, 2 done or disabled */

static int
late_attach(void)
{
    int (*attach)(void);
    if (attach_state != 0)
        return 0;
    attach_state = 1;
    if (getenv("DRPERF_LATE") == NULL) {
        attach_state = 2;
        return 0;
    }
    if (getenv("DRPERF_LATE_VERBOSE") != NULL) {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        fprintf(stderr, "perfmark: attaching DynamoRIO at %ld.%03lds\n", (long)ts.tv_sec, ts.tv_nsec / 1000000);
    }
    attach = (int (*)(void))dlsym(RTLD_DEFAULT, "drperf_attach_now");
    if (attach == NULL || attach() != 0) {
        attach_state = 2;
        return 0;
    }
    attach_state = 2;
    return 1;                   /* now under DynamoRIO: re-enter so it is seen */
}
EXPORT void perfmark_begin(const char *region, const char *state_name, int64_t state_value)
{
    if (attach_state == 0 && late_attach()) {
        /* indirect, so the call lands on the function entry the client watches */
        static void (*volatile again)(const char *, const char *, int64_t) = perfmark_begin;
        again(region, state_name, state_value);
        return;
    }
    (void)region; (void)state_name; (void)state_value;
    __asm__ __volatile__("" ::: "memory");
}
EXPORT void perfmark_begin_v(const char *region, int n, const char *const *names, const int64_t *values)
{
    if (attach_state == 0 && late_attach()) {
        static void (*volatile again)(const char *, int, const char *const *, const int64_t *) =
            perfmark_begin_v;
        again(region, n, names, values);
        return;
    }
    (void)region; (void)n; (void)names; (void)values;
    __asm__ __volatile__("" ::: "memory");
}
EXPORT void perfmark_end(const char *region)
{
    (void)region;
    __asm__ __volatile__("" ::: "memory");
}
EXPORT void perfmark_state(const char *name, const char *value)
{
    (void)name; (void)value;
    __asm__ __volatile__("" ::: "memory");
}

EXPORT int perfmark_event_publish(uint64_t event, uint64_t generation)
{
    (void)event; (void)generation;
    __asm__ __volatile__("" ::: "memory");
    return 0;
}
EXPORT int perfmark_event_waited(uint64_t event, uint64_t generation)
{
    (void)event; (void)generation;
    __asm__ __volatile__("" ::: "memory");
    return 0;
}
