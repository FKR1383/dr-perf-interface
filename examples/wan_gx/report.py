"""Package compact evidence for the final matched full-model comparison."""
import hashlib
import json
from pathlib import Path
import statistics
ROOT=Path(__file__).resolve().parents[2]
RESULTS=ROOT/'out/wan-gx/results'
DEST=Path(__file__).resolve().parent/'evidence'
DEST.mkdir(exist_ok=True)
def read(name): return json.loads((RESULTS/name).read_text())
records={}
for variant in ('baseline','optimized'):
    stem=variant+'-final-profile'
    profile=read(stem+'.json');summary=read(stem+'-summary.json')
    assert summary['validity']==[],summary['validity']
    assert len(profile['runs'])==1 and profile['frames']==81 and profile['steps']==50
    assert all(r['gx_module_instructions']==0 for r in summary['regions'].values())
    assert all(r['dropped']==0 for r in summary['regions'].values())
    assert profile['timing_simulation'] is False and profile['numerical_validation'] is False
    raw=RESULTS/stem/'raw'
    hashes={}
    for path in sorted(raw.iterdir()):
        if path.is_file():
            with path.open('rb') as stream:
                hashes[str(path.relative_to(RESULTS))]=hashlib.file_digest(stream,'sha256').hexdigest()
    host=read(variant+'-native-host-81f50s.json')
    assert host['regions']==[] and host['frames']==81 and host['steps']==50
    records[variant]={'profile':profile,'summary':summary,'raw_sha256':hashes,'unmarked_host':host}
    (DEST/(variant+'.json')).write_text(json.dumps(records[variant],indent=2)+'\n')
a,b=(records[k] for k in ('baseline','optimized'))
assert a['profile']['drperf_binary_sha256']==b['profile']['drperf_binary_sha256']
assert a['profile']['policy']==b['profile']['policy']
assert a['profile']['convolution_backend']==b['profile']['convolution_backend']=='native'
rows=[]
for region,r in sorted(a['summary']['regions'].items(),key=lambda item:-item[1]['own_instructions']):
    opt=b['summary']['regions'][region]
    rows.append(f"| {region} | {r['calls']:,} / {opt['calls']:,} | {r['own_instructions']/1e6:.2f} | {opt['own_instructions']/1e6:.2f} | {100*(1-opt['own_instructions']/r['own_instructions']):.2f}% |")
x=a['summary']['total_marked_own_instructions'];y=b['summary']['total_marked_own_instructions']
base_times=[r['generation_host_seconds'] for r in a['unmarked_host']['runs']]
opt_times=[r['generation_host_seconds'] for r in b['unmarked_host']['runs']]
text=f'''# Measured results: full Wan under GX emulation

Official pretrained Wan2.1-T2V-1.3B, 832x480, 81 frames, 50 UniPC steps,
CFG 5, seed 42, no offload, native CUDA convolution backend. Both variants use
the common control-metadata fixes. See [scope and reproduction](README.md).

Recorded marked CPU instructions: **{x/1e9:.3f} billion -> {y/1e9:.3f} billion
({100*(1-y/x):.2f}% reduction)**. Each region contributes only its own count,
so the total does not double-count nested calls. GX module residue is zero in
both final records; collection validity checks pass. The CPU count includes
annotation overhead and does not include unmarked worker threads or GPU work.

Unmarked GX generation host seconds (three consecutive generations after one
model load per variant):

* Baseline: {', '.join(f'{v:.3f}' for v in base_times)}.
* Optimized: {', '.join(f'{v:.3f}' for v in opt_times)}.
* Median: {statistics.median(base_times):.3f} -> {statistics.median(opt_times):.3f} seconds
  ({100*(1-statistics.median(opt_times)/statistics.median(base_times)):.2f}% lower).

These are emulator host elapsed times, with first-use work included in each
first generation. The experiment is small, sequential, and not a statistical
hardware-performance study. Loading takes about 75 seconds and is excluded
from generation comparisons. No predicted GPU latency or video quality claim
follows from these numbers. Profiled elapsed times in the JSON include DynamoRIO
overhead and are not used to claim speedup.

GX reused an existing 1 GiB shared arena despite the requested 8 GiB policy and
logged soft-real allocations spilling to fake backing. The application completed;
these runs do not use collectives. GX allocation work is excluded from drperf
region counts, but its overhead participates in unmarked host timings. We did
not delete pre-existing shared IPC state. A fresh arena can change these timings.

| Region | Calls baseline / optimized | Baseline M instructions | Optimized M instructions | Reduction |
| --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(rows)+'''

Most regions have insufficient distinct states for an affine fit at this fixed
workload. Mixed VAE convolutions and scheduler steps still have substantial
unexplained cost. A successful structural run or fewer instructions is not an
accepted performance interface. The JSON retains these failed/absent fits,
reconstruction errors, and all exclusion diagnostics.

Compact evidence: [baseline](evidence/baseline.json),
[optimized](evidence/optimized.json). These include source and client hashes,
raw-artifact hashes, runtime policy and package versions. Raw block/trace files
remain under `out/wan-gx/results/{baseline,optimized}-final-profile/raw/`.
Earlier exploratory measurements with narrower CUDA exclusions are superseded
by this matched comparison.
'''
(DEST.parent/'RESULTS.md').write_text(text)
print(text[:1700])
