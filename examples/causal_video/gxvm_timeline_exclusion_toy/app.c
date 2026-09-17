#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static volatile uint64_t host_sink;
__attribute__((noinline, visibility("default"))) uint64_t gxvm_timeline_cpu_units(void) {
    __asm__ volatile("" ::: "memory"); return 0;
}
static void host_loop(unsigned count) {
    for (unsigned i = 0; i < count; ++i) host_sink += (uint64_t)(i & 3u);
}
int main(int argc, char **argv) {
    void *lib;
    uint64_t (*cuda_outer)(unsigned);
    int (*cuda_stream_create)(void);
    int (*cuda_event_record)(void);
    uint64_t (*cuda_observed_events)(void);
    void (*cuda_observed_stamps)(uint64_t *, uint64_t *);
    void (*cuda_observed_event_stamps)(uint64_t *, uint64_t *);
    uint64_t stamp_a, stamp_b, stamp_c, stamp_d, stamp_inside_a, stamp_inside_b;
    uint64_t stamp_stream, stamp_event;
    uint64_t result;
    unsigned count = argc == 2 ? (unsigned)strtoul(argv[1], NULL, 10) : 1000000u;
    lib = dlopen("./gx_cuda.so", RTLD_NOW);
    if (!lib) { puts(dlerror()); return 2; }
    cuda_outer = (uint64_t (*)(unsigned))dlsym(lib, "cudaOuter");
    cuda_stream_create = (int (*)(void))dlsym(lib, "cudaStreamCreate");
    cuda_event_record = (int (*)(void))dlsym(lib, "cudaEventRecord");
    cuda_observed_events = (uint64_t (*)(void))dlsym(lib, "cudaObservedEvents");
    cuda_observed_stamps = (void (*)(uint64_t *, uint64_t *))dlsym(lib, "cudaObservedStamps");
    cuda_observed_event_stamps = (void (*)(uint64_t *, uint64_t *))dlsym(lib, "cudaObservedEventStamps");
    if (!cuda_outer) return 3;
    stamp_a = gxvm_timeline_cpu_units();
    host_loop(count);
    stamp_b = gxvm_timeline_cpu_units();
    if (cuda_stream_create() != 0 || cuda_event_record() != 0) return 4;
    result = cuda_outer(count);
    stamp_c = gxvm_timeline_cpu_units();
    host_loop(count);
    stamp_d = gxvm_timeline_cpu_units();
    cuda_observed_stamps(&stamp_inside_a, &stamp_inside_b);
    cuda_observed_event_stamps(&stamp_stream, &stamp_event);
    printf("CUDA_EXCLUSION_TOY result=%llu host=%llu stream_events=%llu\n",
           (unsigned long long)result, (unsigned long long)host_sink,
           (unsigned long long)cuda_observed_events());
    printf("TIMELINE_STAMPS before=%llu after_host=%llu inside_before=%llu inside_after=%llu after_cuda=%llu after_tail=%llu\n",
           (unsigned long long)stamp_a, (unsigned long long)stamp_b,
           (unsigned long long)stamp_inside_a, (unsigned long long)stamp_inside_b,
           (unsigned long long)stamp_c, (unsigned long long)stamp_d);
    printf("TIMELINE_EVENT_STAMPS stream=%llu event=%llu\n",
           (unsigned long long)stamp_stream, (unsigned long long)stamp_event);
    dlclose(lib);
    return 0;
}
