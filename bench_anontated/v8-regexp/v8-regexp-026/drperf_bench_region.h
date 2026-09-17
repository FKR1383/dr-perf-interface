// Empty-state markers for C++ source-region collection patches.
#ifndef DRPERF_BENCH_REGION_H
#define DRPERF_BENCH_REGION_H

#include "perfmark.h"

namespace drperf_bench {
class Region {
 public:
  explicit Region(const char* name) : name_(name) {
    perfmark_begin_v(name_, 0, nullptr, nullptr);
  }
  ~Region() { perfmark_end(name_); }
  Region(const Region&) = delete;
  Region& operator=(const Region&) = delete;

 private:
  const char* name_;
};
}  // namespace drperf_bench

#define DRPERF_BENCH_JOIN_IMPL(a, b) a##b
#define DRPERF_BENCH_JOIN(a, b) DRPERF_BENCH_JOIN_IMPL(a, b)
#define DRPERF_BENCH_REGION(name) \
  ::drperf_bench::Region DRPERF_BENCH_JOIN(drperf_bench_region_, __LINE__)(name)

#endif
