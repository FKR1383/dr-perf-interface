#!/usr/bin/env python3
"""Regenerate 43 hand-selected RapidJSON cases from the exact pinned checkout."""
import argparse, difflib, hashlib, json, shutil, tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REV='24b5e7a8b27f42fa16b96fc70aade9106cf7102f'
CASES=[]
def add(header, signature, code, purpose, occurrence=0):
    CASES.append((header,signature,code,purpose,occurrence))
obj='Document d(kObjectType); auto& a=d.GetAllocator(); for(int i=0;i<n;++i){ std::string k="key"+std::to_string(i); Value key(k.c_str(),a), v(i); d.AddMember(key,v,a); }'
arr='Document d(kArrayType); auto& a=d.GetAllocator(); for(int i=0;i<n;++i) d.PushBack(i,a);'
add('document.h','GenericValue& CopyFrom(',obj+' Value copy; copy.CopyFrom(d,a); assert(copy==d); d["key0"].SetInt(999); assert(copy["key0"].GetInt()==0);','deep-copy object members without aliasing')
add('document.h','bool operator==(const GenericValue<',arr+' Value copy; copy.CopyFrom(d,a); assert(copy==d); copy[0].SetInt(-1); assert(!(copy==d));','equal and unequal arrays')
add('document.h','GenericValue& MemberReserve(',obj+' d.MemberReserve(n*3,a); assert(d.MemberCount()==unsigned(n)); assert(d.MemberCapacity()>=unsigned(n*3));','reserve object capacity while preserving members')
add('document.h','MemberIterator FindMember(const GenericValue<',obj+' Value key("key0"); assert(d.FindMember(key)!=d.MemberEnd()); Value missing("absent"); assert(d.FindMember(missing)==d.MemberEnd());','member lookup hits and misses')
add('document.h','GenericValue& AddMember(GenericValue& name, GenericValue& value,',obj+' assert(d.MemberCount()==unsigned(n)); assert(d[("key"+std::to_string(n-1)).c_str()].GetInt()==n-1);','growing an object with distinct member names')
add('document.h','void RemoveAllMembers() {',obj+' d.RemoveAllMembers(); assert(d.ObjectEmpty());','destroy all object members')
add('document.h','MemberIterator RemoveMember(MemberIterator m)',obj+' d.RemoveMember(d.MemberBegin()); assert(d.MemberCount()==unsigned(n-1)); assert(!d.HasMember("key0"));','unordered removal and last-member move')
add('document.h','MemberIterator EraseMember(ConstMemberIterator first,',obj+' d.EraseMember(d.MemberBegin(),d.MemberBegin()+n/2); assert(d.MemberCount()==unsigned(n-n/2)); assert(d.MemberBegin()->value.GetInt()==n/2);','ordered member-range erasure')
add('document.h','void Clear() {',arr+' d.Clear(); assert(d.Empty());','clear an array')
add('document.h','GenericValue& Reserve(SizeType',arr+' d.Reserve(n*4,a); assert(d.Size()==unsigned(n)); assert(d.Capacity()>=unsigned(n*4));','array capacity reservation')
add('document.h','GenericValue& PushBack(GenericValue& value,',arr+' assert(d.Size()==unsigned(n)); assert(d[n-1].GetInt()==n-1);','growing array append')
add('document.h','GenericValue& PopBack() {',arr+' d.PopBack(); assert(d.Size()==unsigned(n-1));','array pop and destruction')
add('document.h','ValueIterator Erase(ConstValueIterator first,',arr+' d.Erase(d.Begin(),d.Begin()+n/2); assert(d.Size()==unsigned(n-n/2)); assert(d[0].GetInt()==n/2);','array-range erase and suffix movement')
add('document.h','bool Accept(Handler& handler) const',arr+' TestOutput out; Writer<TestOutput> w(out); assert(d.Accept(w)); Document copy; copy.Parse(out.s.c_str()); assert(copy==d);','DOM traversal and JSON serialization')
add('document.h','void SetStringRaw(StringRefType s, Allocator& allocator)', 'Document d; std::string s(n*7,\'x\'); d.SetString(s.c_str(),s.size(),d.GetAllocator()); assert(d.GetStringLength()==s.size()); assert(std::string(d.GetString())==s);','short and allocated string copying')
add('document.h','void DoCopyMembers(',obj+' Value copy; copy.CopyFrom(d,a); assert(copy.MemberCount()==unsigned(n)); assert(copy==d);','object-copy allocation and member construction')
add('document.h','GenericDocument& ParseStream(InputStream& is)', 'std::string s="["; for(int i=0;i<n;++i){ if(i)s+=","; s+=std::to_string(i); } s+="]"; StringStream stream(s.c_str()); Document d; d.ParseStream(stream); assert(!d.HasParseError()); assert(d.Size()==unsigned(n)); assert(d[n-1].GetInt()==n-1);','parse a varied numeric JSON array')
for signature,call,expect,purpose in [
('bool WriteNull()', 'w.Null()', 'd.IsNull()', 'null serialization'),
('bool WriteBool(bool b)', 'w.Bool(n%2)', 'd.GetBool()==bool(n%2)', 'boolean serialization'),
('bool WriteInt(int i)', 'w.Int(-n*123)', 'd.GetInt()==-n*123', 'signed decimal serialization'),
('bool WriteUint(unsigned u)', 'w.Uint(n*123u)', 'd.GetUint()==n*123u', 'unsigned decimal serialization'),
('bool WriteInt64(int64_t i64)', 'w.Int64(-int64_t(n)*10000000000LL)', 'd.GetInt64()==-int64_t(n)*10000000000LL', 'signed 64-bit serialization'),
('bool WriteUint64(uint64_t u64)', 'w.Uint64(uint64_t(n)*10000000000ULL)', 'd.GetUint64()==uint64_t(n)*10000000000ULL', 'unsigned 64-bit serialization'),
('bool WriteDouble(double d)', 'w.Double(n*0.125)', 'd.GetDouble()==n*0.125', 'floating-point serialization'),
('bool WriteString(const Ch* str,', 'w.String(s.c_str(),s.size())', 'std::string(d.GetString(),d.GetStringLength())==s', 'string escaping with quotes and backslashes'),
('bool WriteRawValue(const Ch* json,', 'w.RawValue(s.c_str(),s.size(),kArrayType)', 'd.IsArray() && d.Size()==unsigned(n)', 'validated raw-array byte copying'),
('void Prefix(Type type)', 'w.StartArray(); for(int i=0;i<n;++i) assert(w.Int(i)); assert(w.EndArray())', 'd.IsArray() && d.Size()==unsigned(n)', 'array separators and nesting bookkeeping'),
]:
    prep='std::string s; for(int i=0;i<n;++i)s+="a\\\"\\\\";'
    if 'RawValue' in signature:prep='std::string s="["; for(int i=0;i<n;++i){if(i)s+=",";s+="1";}s+="]";'
    add('writer.h',signature,prep+' TestOutput out; Writer<TestOutput> w(out); '+call+'; Document d; d.Parse(out.s.c_str()); assert(!d.HasParseError()); assert('+expect+');',purpose)
pathprep='std::string path; for(int i=0;i<n;++i)path+="/k"+std::to_string(i); Pointer p(path.c_str()); assert(p.IsValid());'
add('pointer.h','GenericPointer Append(const Token& token,',pathprep+' Pointer::Token tok={"tail",4,kPointerInvalidIndex}; Pointer q=p.Append(tok); assert(q.GetTokenCount()==unsigned(n+1)); StringBuffer b; q.Stringify(b); assert(std::string(b.GetString())==path+"/tail");','append a pointer token while copying existing tokens')
add('pointer.h','GenericPointer Append(const Ch* name,',pathprep+' Pointer q=p.Append("a/b",3); StringBuffer b; q.Stringify(b); assert(std::string(b.GetString())==path+"/a~1b");','append and escape a pointer name')
add('pointer.h','GenericPointer Append(SizeType index,',pathprep+' Pointer q=p.Append(SizeType(n)); StringBuffer b; q.Stringify(b); assert(std::string(b.GetString())==path+"/"+std::to_string(n));','append a numeric pointer index')
add('pointer.h','bool operator==(const GenericPointer& rhs)',pathprep+' Pointer q(path.c_str()); assert(p==q); assert(!(p==p.Append("x")));','pointer token equality and length mismatch')
add('pointer.h','bool operator<(const GenericPointer& rhs)',pathprep+' Pointer q((path+"z").c_str()); assert(p<q); assert(!(q<p));','lexicographic pointer ordering')
add('pointer.h','ValueType& Create(ValueType& root,',pathprep+' Document d; p.Create(d,d.GetAllocator()).SetInt(9); assert(p.Get(d)->GetInt()==9); bool existed=false; p.Create(d,d.GetAllocator(),&existed); assert(existed);','create missing nested members and revisit existing path')
add('pointer.h','ValueType* Get(ValueType& root,',pathprep+' Document d; p.Create(d,d.GetAllocator()).SetInt(9); assert(p.Get(d)->GetInt()==9); assert(p.Append("missing").Get(d)==nullptr);','nested pointer lookup and missing path')
add('pointer.h','bool Erase(ValueType& root)',pathprep+' Document d; p.Create(d,d.GetAllocator()).SetInt(9); assert(p.Erase(d)); assert(p.Get(d)==nullptr); assert(!p.Erase(d));','erase nested pointer and repeat missing erase')
add('pointer.h','Ch* CopyFromRaw(',pathprep+' Pointer q(p); assert(q==p); assert(q.GetTokenCount()==unsigned(n));','deep-copy pointer token/name buffers')
add('pointer.h','void Parse(const Ch* source, size_t length)',pathprep+' assert(p.GetTokenCount()==unsigned(n)); Pointer escaped("/a~1b/~0"); assert(escaped.IsValid()); assert(std::string(escaped.GetTokens()[0].name)=="a/b"); Pointer bad("/a~2"); assert(!bad.IsValid());','pointer token parsing with escaped and invalid paths')
add('pointer.h','bool Stringify(OutputStream& os) const',pathprep+' StringBuffer b; assert(p.Stringify(b)); assert(std::string(b.GetString())==path); Pointer special("/a~1b/~0"); StringBuffer c; assert(special.Stringify(c)); assert(std::string(c.GetString())=="/a~1b/~0");','pointer escaping during stringification',occurrence=1)
add('stringbuffer.h','void ShrinkToFit()', 'StringBuffer b; for(int i=0;i<n;++i)b.Put(\'x\'); b.ShrinkToFit(); assert(b.GetSize()==unsigned(n)); assert(std::string(b.GetString())==std::string(n,\'x\'));','buffer shrink retaining text')
add('stringbuffer.h','const Ch* GetString() const', 'StringBuffer b; for(int i=0;i<n;++i)b.Put(\'x\'); assert(std::string(b.GetString())==std::string(n,\'x\')); assert(b.GetSize()==unsigned(n));','null-terminate buffer without increasing logical size')
add('allocators.h','void* Malloc(size_t size) {','MemoryPoolAllocator<> a(32); auto p=static_cast<char*>(a.Malloc(n*17)); assert(p); memset(p,\'z\',n*17); assert(p[n*17-1]==\'z\'); assert(a.Size()>=unsigned(n*17));','pool allocation across chunk capacity',occurrence=1)
add('allocators.h','void* Realloc(void* originalPtr,','MemoryPoolAllocator<> a(32); auto p=static_cast<char*>(a.Malloc(n)); memset(p,\'z\',n); a.Malloc(16); auto q=static_cast<char*>(a.Realloc(p,n,n*4)); assert(q); for(int i=0;i<n;++i)assert(q[i]==\'z\');','pool reallocation with intervening allocation and copy',occurrence=1)
add('allocators.h','void Clear() RAPIDJSON_NOEXCEPT','MemoryPoolAllocator<> a(32); for(int i=0;i<n;++i)assert(a.Malloc(64)); a.Clear(); assert(a.Size()==0); assert(a.Malloc(8));','release a varied number of pool chunks')
assert len(CASES)==43,len(CASES)
PREFIX=r'''#include <cassert>
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
'''
def main():
    p=argparse.ArgumentParser();p.add_argument('checkout',type=Path);a=p.parse_args()
    root=a.checkout.resolve(); upstream=ROOT/'upstream/rapidjson';upstream.mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/'license.txt',upstream/'LICENSE')
    support=ROOT/'test-support';support.mkdir(exist_ok=True)
    with tarfile.open(support/'headers.tar.gz','w:gz') as archive:archive.add(root/'include',arcname='include')
    shutil.copy2(ROOT.parents[2]/'perfmark/perfmark.h',support/'perfmark.h')
    for num,(header,sig,body,purpose,occurrence) in enumerate(CASES,1):
        cid=f'nl-{num:03}';rel='include/rapidjson/'+header;raw=(root/rel).read_text();lines=raw.splitlines(keepends=True)
        starts=[i for i,l in enumerate(lines) if sig in l and '{' in l];start=starts[occurrence]
        # All hand-picked function bodies end at the matching indentation.
        end=next(i for i in range(start+1,len(lines)) if lines[i].startswith('    }'))
        marked=lines.copy();marked.insert(start+1,f'        DRPERF_BENCH_REGION("{cid}");\n')
        inc=next(i for i,l in enumerate(marked) if l.startswith('#include'))
        marked.insert(inc,'#include "drperf_bench_region.h"\n')
        dest=ROOT/'cases'/cid; (dest/'tests').mkdir(parents=True,exist_ok=True)
        snapshot=upstream/rel;snapshot.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,snapshot)
        (dest/'region.patch').write_text(''.join(difflib.unified_diff(lines,marked,fromfile='a/'+rel,tofile='b/'+rel)))
        code='#define CASE_ID "'+cid+'"\n'+PREFIX+'\nvoid test(int n) {\n'+body+'\n}\nint main(){ for(int n: {1,2,7,16,65}) {int old=hits; test(n); assert(hits>old); assert(hits==ends);} std::cout << CASE_ID << ": marker and assertions passed\\n"; }\n'
        (dest/'tests/case.cpp').write_text(code)
        command=['{python}','tests/run_case.py','--source-root','{source_root}']
        resources=[]
        for name in ('run_case.py','headers.tar.gz','perfmark.h'):
            f=support/name
            resources.append({'source':'../../test-support/'+name,'destination':'tests/'+name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
        data={'schema_version':1,'id':cid,'title':'RapidJSON: '+purpose,'language':'cpp','source':{'repository':'https://github.com/Tencent/rapidjson','revision':REV,'path':rel,'snapshot':'../../upstream/rapidjson/'+rel,'sha256':hashlib.sha256((root/rel).read_bytes()).hexdigest()},'region':{'symbol':sig.split('{')[0].strip(),'start_line':start+1,'end_line':end+1,'kind':'function'},'marker':{'kind':'cpp-raii','name':cid,'pcvs':[]},'status':'collected','build_status':'not-built','workload':{'description':purpose+'; sizes 1, 2, 7, 16, 65 with semantic assertions and target marker reachability at every size.','command':command},'source_family':'rapidjson:'+header+':'+str(start+1),'tests':{'files':['tests/case.cpp'],'resources':resources,'command':command,'validation':{'status':'not-run','details':'Native compile and marker-entry assertions pending.'}}}
        (dest/'case.json').write_text(json.dumps(data,indent=2)+'\n')
        (dest/'task.md').write_text(f'# {cid}: {purpose}\n\nUse the empty region marker in `{rel}`. Explain its cost with entry-state expressions, using small workloads. Preserve all behavior assertions.\n\nRun `python3 tests/run_case.py --source-root .` from the export. The driver compiles the exact pinned headers with the marked source overlaid, then checks output semantics and target entry at five sizes. Requires Python 3 and a C++11 compiler.\n')
        (dest/'reference.md').write_text(f'# Evaluator reference: {cid}\n\nPinned source: https://github.com/Tencent/rapidjson/blob/{REV}/{rel}#L{start+1}\n\nTarget: `{sig}` (occurrence {occurrence+1}). Workload: {purpose}. Sizes 1, 2, 7, 16, 65; each must enter the marker and satisfy exact semantic assertions. These are separate function regions, some in the same call chain; split by upstream project/call family to avoid evaluation leakage.\n\nThis is a collection lead, not a demonstrated optimization. Native observer assertions establish execution, not drperf instruction counts or a fitted interface.\n')
if __name__=='__main__':main()
