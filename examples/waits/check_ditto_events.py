#!/usr/bin/env python3
"""Annotate a build copy of Ditto's real candidate scheduler and probe its future.

Leaves the user's source, installed runtime, and serving profiles untouched.
No torch, CUDA, GX, fake candidate algorithm, or GPU is used in this CPU test.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
import event_model
import explorer
import runner

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ditto', type=Path, default=Path('/home/ubuntu/compression/ditto_kv'))
args = parser.parse_args()
native = args.ditto / 'src/compressor/native'
original = (native / 'ditto_runtime.cpp').read_text()
out = ROOT / 'out/waits/ditto-events'
out.mkdir(parents=True, exist_ok=True)


def replace_once(source, old, new):
    assert source.count(old) == 1, ('Upstream changed; review annotation placement', old)
    return source.replace(old, new)


annotated = '#include "perfmark.h"\n#include <atomic>\n' + original
annotated = replace_once(annotated, 'namespace {', 'namespace {\nstd::atomic<uint64_t> annotation_next_event{1};')
annotated = replace_once(annotated,
    'Future submit(const int32_t* tokens, size_t count, int32_t min_match) {',
    'Future submit(const int32_t* tokens, size_t count, int32_t min_match, uint64_t* event_out = nullptr) {')
annotated = replace_once(annotated, '            return found->second.first;',
    '            if (event_out) *event_out = annotation_events.at(key);\n            return found->second.first;')
annotated = replace_once(annotated, '        Future future = pool.submit(',
    '        const uint64_t event = annotation_next_event++;\n'
    '        annotation_events[key] = event;\n'
    '        if (event_out) *event_out = event;\n'
    '        Future future = pool.submit(')
annotated = replace_once(annotated,
    '[tokens = std::move(copy), min_match]() {\n                return build_candidates(tokens, min_match);',
    '[tokens = std::move(copy), min_match, event]() {\n'
    '                perfmark_begin("candidates.build", "tokens", tokens.size());\n'
    '                auto result = build_candidates(tokens, min_match);\n'
    '                perfmark_event_publish(event, 1);\n'
    '                perfmark_end("candidates.build");\n'
    '                return result;')
annotated = replace_once(annotated, '            cache.erase(victim);',
    '            cache.erase(victim);\n            annotation_events.erase(victim);')
annotated = replace_once(annotated, '    ThreadPool pool;',
    '    std::unordered_map<std::string, uint64_t> annotation_events;\n    ThreadPool pool;')
annotated = replace_once(annotated,
    '        const auto result = context->submit(tokens, ntokens, min_match).get();',
    '        uint64_t event;\n'
    '        auto future = context->submit(tokens, ntokens, min_match, &event);\n'
    '#ifdef FALSE_WAITED\n'
    '        perfmark_event_waited(event, 1); // Deliberately premature annotation.\n'
    '#endif\n'
    '        const auto result = future.get();\n'
    '#ifndef FALSE_WAITED\n'
    '        perfmark_event_waited(event, 1);\n'
    '#endif')
(out / 'ditto_runtime.cpp').write_text(annotated)
(out / 'annotations.patch').write_text(''.join(difflib.unified_diff(
    original.splitlines(True), annotated.splitlines(True),
    fromfile=str(native / 'ditto_runtime.cpp'), tofile=str(out / 'ditto_runtime.cpp'))))

common = ['g++', '-O2', '-std=c++17', '-pthread', '-I'+str(native), '-I'+str(ROOT/'perfmark'),
          '-L'+str(ROOT/'build'), '-Wl,-rpath,'+str(ROOT/'build')]
for name, source, extra in [('original',native/'ditto_runtime.cpp',[]),
                             ('correct',out/'ditto_runtime.cpp',[]),
                             ('premature',out/'ditto_runtime.cpp',['-DFALSE_WAITED'])]:
    subprocess.run(common+['-shared','-fPIC',str(source),'-lperfmark','-ldl',
                           '-o',str(out/(name+'.so'))]+extra, check=True)

driver = out/'driver.cpp'
driver.write_text(r'''
#include "ditto_runtime.h"
#include "perfmark.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <dlfcn.h>
#include <unistd.h>
#include <vector>
int main(int argc, char **argv) {
    assert(argc == 2);
    void* lib = dlopen(argv[1], RTLD_NOW); assert(lib);
    auto create = (decltype(&ditto_context_create))dlsym(lib, "ditto_context_create");
    auto destroy = (decltype(&ditto_context_destroy))dlsym(lib, "ditto_context_destroy");
    auto prefetch = (decltype(&ditto_candidates_prefetch))dlsym(lib, "ditto_candidates_prefetch");
    auto get = (decltype(&ditto_candidates_get))dlsym(lib, "ditto_candidates_get");
    perfmark_begin("capture", "n", 1); perfmark_end("capture");
    ditto_context_options options{2, 2}; ditto_report report{};
    auto context = create(&options, &report); assert(context);
    uint64_t checksum = 1469598103934665603ull;
    // Fifth batch revisits an evicted key: the event must get a fresh identity.
    for (int n : {8, 64, 256, 1024, 8}) {
        std::vector<int32_t> tokens(n), result(n * 7);
        for (int i = 0; i < n; ++i) tokens[i] = i % 17;
        perfmark_begin("candidates.prefetch", "tokens", n);
        assert(prefetch(context, tokens.data(), n, 3, &report) == DITTO_OK);
        perfmark_end("candidates.prefetch");
        // Baseline deliberately allows publication before get: a premature
        // waited marker looks valid until the automatic delay probe runs.
        usleep(200000);
        for (int cached : {0, 1}) {
            const char *names[] = {"tokens", "cached"}; int64_t values[] = {n, cached};
            perfmark_begin_v("candidates.get", 2, names, values);
            assert(get(context, tokens.data(), n, 3, result.data(), result.size(), &report) == DITTO_OK);
            perfmark_end("candidates.get");
            for (int32_t value : result) { checksum ^= (uint32_t)value; checksum *= 1099511628211ull; }
        }
    }
    destroy(context);
    printf("checksum=%llu\n", (unsigned long long)checksum);
}
''')
subprocess.run(common+[str(driver),'-lperfmark','-ldl','-o',str(out/'demo')], check=True)
expected = subprocess.check_output([str(out/'demo'),str(out/'original.so')],text=True).strip()


def run(name, label, delay=0):
    folder = out/(name+'-'+label)
    for previous in folder.glob('run.*.json*'): previous.unlink()
    with patch.dict(os.environ, {'DRPERF_WAITS':'1','DRPERF_FOLLOW_THREADS':'0',
         'DRPERF_WAIT_DELAY_KIND':'event','DRPERF_WAIT_DELAY_REGION':'candidates.build',
         'DRPERF_WAIT_DELAY_MS':str(delay)}):
        rc, log, _ = runner.run([str(out/'demo'),str(out/(name+'.so'))],str(folder),timeout=60)
    assert rc == 0, log
    assert expected in log, (expected, log)
    profile = explorer.build_model(folder, out, ['ditto_runtime.cpp','driver.cpp'], discover=False)
    assert not profile['validity']['errors'] and not profile['validity']['traceErrors'], profile['validity']
    explorer.write_model(profile,out/(name+'-'+label+'.drperf.json'))
    return profile['eventModel']


results = {'source':str(native/'ditto_runtime.cpp'),
    'sourceSha256':hashlib.sha256(original.encode()).hexdigest(),
    'output':expected, 'scope':'Actual Ditto CPU candidate scheduler, 2 workers, cache capacity 2; no model/GPU run.'}
for name in ['correct','premature']:
    baseline = run(name,'baseline')
    assert baseline['status'] == 'ordered', baseline
    assert len(baseline['edges']) == 10
    plan = next(p for p in event_model.probe_plan(baseline) if p['region']=='candidates.build')
    probe = run(name,'probe',plan['delayMs'])
    assert not probe['unverified'], probe
    assert bool(probe['violations']) == (name=='premature'), probe
    assert len({e['publication'] for e in probe['edges']}) == 5
    results[name] = {'baseline':baseline,'plan':plan,'probe':probe}
    print(name, 'baseline='+baseline['status'], 'delay='+str(plan['delayMs'])+'ms',
          'probe='+probe['status'], 'violations='+str(len(probe['violations'])), flush=True)
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(expected)
print(out/'results.json')
