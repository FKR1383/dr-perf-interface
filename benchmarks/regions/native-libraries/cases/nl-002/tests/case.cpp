#define CASE_ID "nl-002"
#include <cassert>
#include <cstring>
#include <string>
#include <iostream>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/pointer.h"
#include "rapidjson/stringbuffer.h"
using namespace rapidjson;
struct TestOutput { typedef char Ch; std::string s; void Put(char c){s+=c;} void Flush(){} };
static int hits=0, ends=0;
#ifdef DRPERF_BENCH_REAL
extern "C" void __real_perfmark_begin_v(const char*,int,const char* const*,const int64_t*);
extern "C" void __real_perfmark_end(const char*);
#define OBSERVE_BEGIN __wrap_perfmark_begin_v
#define OBSERVE_END __wrap_perfmark_end
#else
#define OBSERVE_BEGIN perfmark_begin_v
#define OBSERVE_END perfmark_end
#endif
extern "C" void OBSERVE_BEGIN(const char* region,int n,const char* const* names,const int64_t* values) {
 assert(std::string(region)==CASE_ID); assert(n>=0 && (n==0 || (names && values))); ++hits;
#ifdef DRPERF_BENCH_REAL
 __real_perfmark_begin_v(region,n,names,values);
#endif
}
extern "C" void OBSERVE_END(const char* region) {
 assert(std::string(region)==CASE_ID); ++ends;
#ifdef DRPERF_BENCH_REAL
 __real_perfmark_end(region);
#endif
}

void test(int n) {
Document d(kArrayType); auto& a=d.GetAllocator(); for(int i=0;i<n;++i) d.PushBack(i,a); Value copy; copy.CopyFrom(d,a); assert(copy==d); copy[0].SetInt(-1); assert(!(copy==d));
}
int main(){ for(int n: {1,2,7,16,65}) {int old=hits; test(n); assert(hits>old); assert(hits==ends);} std::cout << CASE_ID << ": marker and assertions passed\n"; }
