#!/usr/bin/env python3
"""Differential correctness and interleaved native timing for the quote-only workload."""
import contextlib, hashlib, importlib.util, itertools, json, random, statistics, sys, time, types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
@contextlib.contextmanager
def region(*args,**kwargs): yield
marker=types.ModuleType('perfmark');marker.region=region;sys.modules['perfmark']=marker
def load(name,tree):
    path=ROOT/tree/'growth-multifold/aq-003/Lib/http/cookies.py'
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m._unquote,hashlib.sha256(path.read_bytes()).hexdigest()
before,bhash=load('before','bench_anontated');after,ahash=load('after','bench_optimized')
checked=0

def check(value):
    global checked
    assert before(value)==after(value),repr(value)
    checked+=1
alphabet='a\\"047';rng=random.Random(0)
for length in range(7):
    for chars in itertools.product(alphabet,repeat=length):check('"'+''.join(chars)+'"')
for _ in range(10000):check('"'+''.join(rng.choice(alphabet) for _ in range(rng.randrange(80)))+'"')
for value in (None,'plain','', '"', '\\', '"a\\\nb"', '"a\\\rb"', '"λ\\"雪"'):check(value)
for n in (1,2,4,8,16,32,64,128,256,512):
    for chunk in (r'a\"',r'a\042',r'a\777',r'a\000',r'a\\'):check('"'+chunk*n+'"')
rows=[]
for n in (16,32,64,128,256,512):
    value='"'+r'a\"'*n+'"';expected='a"'*n
    assert before(value)==after(value)==expected
    samples={'before':[],'after':[]}
    for _ in range(20):before(value);after(value)
    for trial in range(11):
        order=[('before',before),('after',after)]
        if trial%2:order.reverse()
        for name,fn in order:
            start=time.perf_counter_ns()
            for _ in range(100):fn(value)
            samples[name].append((time.perf_counter_ns()-start)/100)
    b=statistics.median(samples['before']);a=statistics.median(samples['after'])
    rows.append({'repetitions':n,'input_characters':len(value),'before_ns_per_call':b,'after_ns_per_call':a,'native_speedup':b/a,'samples_ns_per_call':samples})
result={'correctness':{'checked':checked,'mismatches':0,'seed':0},'source_sha256':{'before':bhash,'after':ahash},'timing':{'clock':'perf_counter_ns','rounds':11,'calls_per_round':100,'warmup_calls':20,'order':'alternating before/after','marker':'same no-op Python context manager on both; PCV evaluation retained','scope':'_unquote call only, outside DynamoRIO; not end-to-end HTTP throughput','states':rows}}
(HERE/'evidence/validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'correctness':result['correctness'],'native_speedups':[round(r['native_speedup'],2) for r in rows]}))
