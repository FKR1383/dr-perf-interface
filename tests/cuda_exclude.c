#include <stdint.h>
#ifdef EMULATOR
extern void host_helper(int n);
__attribute__((noinline)) void cudaInner(int n) { host_helper(n); }
__attribute__((noinline)) void cudaOuter(int n) { cudaInner(n); host_helper(n); }
__attribute__((noinline)) void __cudaPrivate(int n) { cudaOuter(n); }
__attribute__((noinline)) void cublasFake(int n) { host_helper(n); }
#else
#include "../perfmark/perfmark.h"
extern void __cudaPrivate(int n);
extern void cublasFake(int n);
volatile uint64_t sink;
__attribute__((noinline)) void host_helper(int n) {
    for (int i = 0; i < n; ++i) sink += (uint64_t)i;
}
int main(void) {
    for (int n = 1000; n <= 3000; n += 1000) {
        perfmark_begin("emulated", "n", n);
        __cudaPrivate(n);
        cublasFake(n);
        host_helper(16);
        perfmark_end("emulated");
        perfmark_begin("after", "n", n);
        host_helper(n);
        perfmark_end("after");
    }
    return sink == 0;
}
#endif
