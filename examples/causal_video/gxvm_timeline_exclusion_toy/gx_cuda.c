#include <stdint.h>
static volatile uint64_t sink;
static volatile uint64_t stream_events;
extern uint64_t gxvm_timeline_cpu_units(void);
static uint64_t cuda_before, cuda_after;
static uint64_t stream_stamp, event_stamp;
__attribute__((noinline, visibility("default"))) int cudaStreamCreate(void) {
    stream_events += 1;
    stream_stamp = gxvm_timeline_cpu_units();
    return 0;
}
__attribute__((noinline, visibility("default"))) int cudaEventRecord(void) {
    stream_events += 10;
    event_stamp = gxvm_timeline_cpu_units();
    return 0;
}
__attribute__((noinline, visibility("default"))) uint64_t cudaObservedEvents(void) {
    return stream_events;
}
__attribute__((noinline, visibility("default"))) void cudaObservedStamps(uint64_t *a, uint64_t *b) {
    *a = cuda_before; *b = cuda_after;
}
__attribute__((noinline, visibility("default"))) void cudaObservedEventStamps(uint64_t *a, uint64_t *b) {
    *a = stream_stamp; *b = event_stamp;
}
__attribute__((noinline, visibility("default"))) uint64_t cudaInner(unsigned count) {
    for (unsigned i = 0; i < count; ++i) sink += (uint64_t)(i & 7u);
    return sink;
}
__attribute__((noinline, visibility("default"))) uint64_t cudaOuter(unsigned count) {
    cuda_before = gxvm_timeline_cpu_units();
    uint64_t first = cudaInner(count);
    for (unsigned i = 0; i < count; ++i) sink += (uint64_t)(i & 3u);
    cuda_after = gxvm_timeline_cpu_units();
    return first + sink;
}
