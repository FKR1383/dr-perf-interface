"""Retain the original measurements and report subsequent matched passes."""
import hashlib
import json
from pathlib import Path
import statistics
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RESULTS=ROOT/'out/wan-gx/results'
def read(p): return json.loads(p.read_text())
records={'Baseline':read(HERE/'evidence/baseline.json'),'First pass':read(HERE/'evidence/optimized.json')}
for name,stem in [('Metadata/layout pass','optimized-more'),('Dispatch pass','optimized-dispatch')]:
    profile=read(RESULTS/(stem+'-profile.json'))
    summary=read(RESULTS/(stem+'-profile-summary.json'))
    host=read(RESULTS/(stem+'-host.json'))
    reference=records['Baseline']['profile']
    assert summary['validity']==[] and summary['regions']
    assert all(v['gx_module_instructions']==0 and v['dropped']==0 for v in summary['regions'].values())
    assert profile['drperf_binary_sha256']==reference['drperf_binary_sha256']
    assert profile['policy']==reference['policy']
    assert profile['frames']==81 and profile['steps']==50 and len(profile['runs'])==1
    assert profile['convolution_backend']=='native' and profile['packages']==reference['packages']
    assert profile['timing_simulation'] is False and host['regions']==[]
    assert host['frames']==81 and host['steps']==50 and len(host['runs'])==3
    assert host['source_sha256']==profile['source_sha256']
    hashes={}
    for path in sorted((RESULTS/(stem+'-profile')).rglob('*')):
        if path.is_file():
            with path.open('rb') as f: hashes[str(path.relative_to(RESULTS))]=hashlib.file_digest(f,'sha256').hexdigest()
    record=dict(profile=profile,summary=summary,unmarked_host=host,raw_sha256=hashes)
    (HERE/'evidence'/(stem+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    records[name]=record
base=records['Baseline']['summary']['total_marked_own_instructions']
rows=[]
for name,r in records.items():
    cost=r['summary']['total_marked_own_instructions']
    times=[v['generation_host_seconds'] for v in r['unmarked_host']['runs']]
    rows.append(f"| {name} | {cost/1e9:.3f} | {100*(1-cost/base):.2f}% | {', '.join(f'{t:.3f}' for t in times)} | {statistics.median(times):.3f} |")
a=records['First pass']['summary']['regions'];b=records['Dispatch pass']['summary']['regions']
regions=[]
for name in sorted(a,key=lambda n:-a[n]['own_instructions']):
    x,y=a[name]['own_instructions'],b[name]['own_instructions']
    regions.append(f"| {name} | {x/1e6:.2f} | {y/1e6:.2f} | {100*(1-y/x):.2f}% |")
text='''# Further Wan CPU optimization passes

Same official pretrained model, 832x480, 81 frames, 50 steps, CFG, seed,
precision policy, native convolution backend, and drperf binary/scope as the
[first comparison](RESULTS.md). Every profile completes the full schedule and
VAE decode, has zero GX module residue and passes collection validity checks.

| Variant | Marked CPU instructions, billions | Reduction vs baseline | Unmarked host seconds, 3 generations | Median seconds |
| --- | ---: | ---: | --- | ---: |
'''+ '\n'.join(rows)+'''

## Changes and drperf feedback

1. **Attention metadata:** build cumulative lengths from CPU-owned lengths,
   reuse them across a generation, and keep the same variable-length
   FlashAttention entry point. CUDA-owned lengths retain the original path.
2. **Rotary work:** reuse grids for the generation and use a batched expression
   for a single unpadded sequence, avoiding empty concatenations and a stack.
   Multi-batch and padded inputs retain the general path.
3. **Patch embedding:** its temporal kernel is one, so apply the same weights
   as 2D convolutions over a batch of frames. Temporal kernels retain Conv3d.
   This changes the convolution implementation, not the model's mathematical
   operation; its measured benefit is specific to the native backend used here.
4. **Layout correction:** eliminating a concatenation initially increased layer
   norm cost because it removed a contiguous copy. drperf exposed the regression.
   Make the token input contiguous once, before the transformer blocks.
5. **Precision-scope dispatch:** remove three per-block autocast contexts around
   only add/multiply/chunk. The installed PyTorch CUDA dispatcher registers all
   three as autocast fallthrough; a test verifies that prerequisite. Scopes
   around operations that need float32 computation remain.
6. **RMSNorm:** use PyTorch's RMSNorm operation on float32 inputs, retaining the
   original output cast and subsequent weight multiplication.
7. **VAE:** avoid padding/copying when every requested padding amount is zero.

The patches are cumulative: [first pass](optimization.patch),
[metadata/layout pass](optimization-more.patch), then
[dispatch pass](optimization-dispatch.patch). Existing first-pass evidence is
preserved. All 25 marked region boundaries remain the same; marker bookkeeping
inside enclosing regions remains included.

| Region | First pass M instructions | Dispatch pass M instructions | Further reduction |
| --- | ---: | ---: | ---: |
'''+ '\n'.join(regions)+'''

## Validation and limits

`test_more.py` includes the original nonzero transformer-output, context-mutation,
cache-cleanup and VAE checks. It adds exact rotary comparisons for padded/full
inputs, batches 1/2 and float32/bfloat16; grouped/strided/noncontiguous framewise
convolution checks and a temporal-kernel fallback; the actual attention-preparation
bodies with a CPU reference attention kernel; metadata mutation/cache cleanup;
and RMSNorm float32/bfloat16 comparisons. The convolution and RMSNorm checks use
explicit floating-point tolerances; additional CPU bfloat16 framewise convolution
cases match exactly. No GPU numerical-equivalence or generated
video-quality claim follows from CPU tests or GX, particularly for the new
convolution/RMSNorm implementations. Model-specific rewrites assume the fixed
inference configuration, without custom module hooks.

These remain emulator host timings: three consecutive generations per variant,
model loading excluded, no GPU timing simulation. The shared-arena spill and
native-convolution limitations from the first comparison still apply. Many
regions still have insufficient distinct PCV states for an affine fit; VAE and
scheduler fits still contain substantial unexplained work. The reductions are
measured CPU work, not a claim that every performance interface is accepted.

## Reproduce the extra passes

After preparing the first-pass `out/wan-gx/optimized` tree:

```
python3 examples/wan_gx/optimize_more.py
python3 examples/wan_gx/optimize_dispatch.py
make -f examples/wan_gx/run.mk resume
make -f examples/wan_gx/run.mk command CMD='OMP_NUM_THREADS=1 WAN_OPTIMIZED_TREE=optimized-dispatch python3 /workspace/examples/wan_gx/test_more.py'
```

Use the same [profiling and host-time commands](README.md#reproduction), with
`--tree /workspace/out/wan-gx/optimized-dispatch` and fresh output paths.
`report_more.py` validates and packages the completed measurements.
Compact evidence: [metadata/layout pass](evidence/optimized-more.json),
[dispatch pass](evidence/optimized-dispatch.json).
'''
(HERE/'MORE_RESULTS.md').write_text(text)
print(text[:1600])
