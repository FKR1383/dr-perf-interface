// Native target-entry observer for the pinned compiler coverage build.
// This records entry only; it does not measure instruction counts or fit PCVs.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
extern "C" void perfmark_begin_v(const char* name, int, const char* const*, const int64_t*) {
    static FILE* output = []() -> FILE* {
        const char* path = std::getenv("DRPERF_ENTRY_LOG");
        return path ? std::fopen(path, "a") : nullptr;
    }();
    if (output) { std::fprintf(output, "%s\n", name); std::fflush(output); }
}
extern "C" void perfmark_end(const char*) {}
