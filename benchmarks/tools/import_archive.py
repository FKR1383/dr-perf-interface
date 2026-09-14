import hashlib
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description='Import historical evidence, never execute archived scripts.')
parser.add_argument('archive', type=Path)
parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
ROOT = args.destination.resolve()
ARCHIVE = args.archive.resolve()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.prepare import SPECS

# IDs and public titles deliberately do not disclose the historical finding.
# Each tuple: id, heading prefix, public target, expected factors, source assets.
CASES = [
 ('ftl_01', '## Case 1.', 'FTL admission limit', ['resident superblock count', 'commits and frees determine resident state; a small measured scan need not warrant a fix'], ['vllm-ditto/examples/cases/step_admission.py']),
 ('ftl_02', '## Case 2.', 'FTL lookup call sites', ['superblock occupancy (resident I/O blocks)', 'lookup clones a block map at three read-only call sites'], ['vllm-ditto/examples/cases/lookup_sites.py', 'vllm-ditto/examples/cases/equivalence.py']),
 ('ftl_03', '## Case 3.', 'FTL batch binding', ['request count independently of directory blocks and superblocks', 'container occupancy, key representation and growth history; distinguish old and new implementations'], ['vllm-ditto/examples/cases/bind_at_size.py', 'vllm-ditto/examples/cases/bind_grid.py', 'vllm-ditto/examples/cases/bind_grow.py']),
 ('ftl_04', '## Case 4.', 'FTL statistics updates', ['number of distinct counter entries', 'full statistics dictionary conversion per count update'], ['vllm-ditto/examples/cases/count_stats.py']),
 ('ftl_05', '## Case 5.', 'Python container updates', ['table capacity / resize headroom as well as live entry count', 'conditional rehash work; an exact-size resize probe is not a portable complexity model'], ['examples/hashmap_internal.py']),
 ('ftl_06', '## Case 6.', 'FTL block ordering', ['block count and its square', 'map getter copies all blocks once for each offset'], ['vllm-ditto/examples/cases/ordered_blocks.py']),
 ('ftl_07', '## Case 7.', 'FTL row allocation', ['number of exhausted slabs scanned', 'indicator for allocating a new slab'], ['vllm-ditto/examples/cases/ensure_row_slabs.py']),
 ('ftl_08', '## Case 8.', 'FTL digest retirement', ['digest table size per retired block', 'retired block count times digest table size for a batch region'], ['vllm-ditto/examples/cases/digest_scan.py']),
 ('vllm_a', '### vLLM case A.', 'vLLM scheduling and input preparation', ['running requests and scheduled tokens varied independently', 'large per-step constant and rebuilding cached request data'], ['examples/vllm_run2.py', 'examples/vllm_mark2.py', 'patches/vllm_prepare_inputs.patch', 'patches/vllm_cached_request_data.patch']),
 ('vllm_b', '### vLLM case B.', 'vLLM request admission', ['prompt token count and per-request constant', 'full hash block count (128-token staircase in the archived configuration)', 'input validation scans and request parameter deepcopy'], ['examples/vllm_run_req.py', 'examples/vllm_mark_req.py', 'patches/vllm_admission.patch', 'patches/vllm_request_init.patch']),
 ('vllm_c', '### vLLM case C.', 'vLLM input batch arrivals and departures', ['prompt tokens on admission', 'rows actually moved / holes on departure, not merely token count', 'metadata rebuilding'], ['examples/vllm_run_batch.py', 'examples/vllm_mark_batch.py', 'patches/vllm_input_batch.patch']),
 ('vllm_d', '### vLLM case D.', 'vLLM sampling', ['total historical tokens across requests', 'maximum history length and batch size, separated experimentally', 'reprocessing growing histories each step produces cumulative quadratic work'], ['examples/vllm_run_samp.py', 'examples/mark_samp.py', 'patches/vllm_penalties.patch']),
 ('vllm_e', '### vLLM case E.', 'vLLM output processing', ['output count and active request count', 'measurement overhead: historical nested markers dominated the first apparent surprise; require marker-free control'], ['examples/vllm_run_out.py', 'patches/vllm_output_path.patch']),
 ('vllm_f', '### vLLM case F.', 'vLLM prefix cache management', ['new/full/cached block counts', 'resident KV conservation across allocation and release', 'distinguish a no-op hash call from one processing new blocks'], ['examples/vllm_run2_kv.py', 'examples/vllm_mark_kv.py', 'patches/vllm_kv_hash.patch', 'patches/vllm_common_prefix.patch']),
 ('vllm_g', '### vLLM case G.', 'vLLM scheduling under load', ['actual waiting-head examinations, not queue length alone', 'running requests scanned during preemption', 'saturated running batch can give waiting count zero effect; consult correction in record'], ['examples/vllm_run_sched.py', 'examples/vllm_mark_sched.py', 'patches/vllm_sched_head.patch', 'patches/vllm_sched_preempt.patch']),
 ('vllm_h', '### vLLM case H.', 'vLLM speculative decoding', ['context length, request count and number of proposed/accepted tokens', 'ngram search and gather/index work; nonlinear context-dependent repeated work', 'separate hit and miss regimes; warm up JIT before measuring'], ['examples/vllm_run_spec.py', 'patches/vllm_ngram_index.patch']),
 ('vllm_h2', '### vLLM case H2.', 'vLLM stopping and log probabilities', ['all batch rows versus rows requesting logprobs', 'enabling logprobs for one request triggers work across the batch', 'stop-string/min-token paths are cheap in recorded regime; do not invent a dominant term'], ['examples/vllm_run_spec.py', 'patches/vllm_stop.patch', 'patches/apply_logprobs_rows.py']),
 ('wan_a', '## Video generation: Wan 2.1', 'Wan video pipeline host execution', ['spatial/temporal shape products and repeated denoising steps / CFG passes', 'repeated rotary and text preparation independent of changing latent values', 'VAE concatenation over accumulated frames'], ['videogen/run_tiny.py', 'videogen/mark_wan.py', 'videogen/patches/wan_rope.patch', 'videogen/patches/wan_text_embed.patch', 'videogen/patches/wan_vae_cat.patch', 'videogen/patches/wan_misc.patch']),
 ('wan_b', '### Wan case B.', 'Wan callbacks, rotary application and VAE paths', ['rotary tensor element count', 'callback selections and live local objects', 'posterior construction and tile/row counts'], ['videogen/run_more.py', 'videogen/mark_more.py', 'videogen/patches/wan_more_cb_locals.patch', 'videogen/patches/wan_more_dgd_lazy.patch', 'videogen/patches/wan_more_rope_apply.patch']),
 ('wan_c', '### Wan case C.', 'Wan transformer step execution', ['prompt length / projected tensor sizes', 'layer count times steps times CFG passes', 'cross-attention key/value projection repeats despite unchanged prompt'], ['videogen/run_tax.py', 'videogen/mark_tax_probe.py', 'videogen/patches/wan_tax.patch', 'videogen/verify_tax.py']),
 ('wan_d', '### Wan case D.', 'Wan prompt encoding', ['padded sequence length squared, batch and layer counts', 'real token count separated from padding length', 'attention follows padded length even when real prompt length is fixed'], ['videogen/run_t5.py', 'videogen/mark_t5.py', 'videogen/patches/wan_t5_shortpad.patch', 'videogen/equiv_t5.py']),
 ('kimi_cold', '## A pure-CPU system:', 'Kimi CLI startup', ['tool identity and imported dependency set', 'startup/import fixed costs; tool count alone is insufficient'], ['startup/run_kimi.py', 'startup/mark.py', 'startup/bench.py', 'kimi_fixes.patch']),
 ('kimi_session', '## The same CLI, running:', 'Kimi CLI session processing', ['message count and characters per message', 'tool schema size / identity and session steps', 'repeated token counting and schema conversion'], ['startup/run_tokens.py', 'startup/mark_tokens.py', 'startup/run_agent_kimi.py', 'startup/stub_llm.py', 'kimi_step_fixes.patch']),
 ('spec2lean', '## A second codebase,', 'spec2lean document processing', ['subtree nodes times total document nodes', 'anchor count times document elements', 'repeated whole-document fetch/traversal inside a local walk'], ['s2l/run_tree.py', 's2l/run_anchor.py', 's2l/mark.py', 's2l/nodes.json', 's2l_fixes.patch']),
 ('sqlglot', '## A third-party library:', 'SQL query optimization', ['join count and its square', 'repeated expression-tree walks whose size also grows with joins; no optimization required'], ['oss/run_sqlglot.py']),
 ('libcst', '## libcst:', 'Python source parsing', ['expression chain length and its square', 'left-recursive clone behavior for binary, union and call chains'], ['oss/run_libcst.py', 'oss/equiv_libcst.py', 'libcst_fixes.patch']),
 ('framepack', '## FramePack:', 'FramePack output saving', ['accumulated frames saved on each section', 'section count and cumulative sum of saved prefixes', 'forward and reverse entry points differ; saved-frame count differs from newly generated frames'], ['videogen/causal/drperf_framepack.py', 'videogen/causal/test_incremental.py', 'videogen/causal/test_reverse.py', 'framepack_fix.patch']),
 ('gradio', '## Gradio:', 'Gradio streaming chat processing', ['conversation messages reprocessed for every streamed chunk', 'growing response length in diff generation', 'distinguish chunk count from conversation size'], ['more/drperf_gradio.py']),
 ('comfyui', '## ComfyUI:', 'ComfyUI execution cache keys', ['ancestor depth / traversal work rather than just graph node count', 'sum of depths for a chain is quadratic; a wide graph with the same node count is a control', 'repeated ancestor signature construction and hashing'], ['comfy/drperf_cachekey.py', 'comfy/verify_comfy.py', 'comfyui_cachekey.patch']),
]

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')

def copy(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {'archive_path': str(src.relative_to(ARCHIVE)), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest()}

lines = (ARCHIVE/'CASES.md').read_text().splitlines(keepends=True)
starts = {id: next(i for i,l in enumerate(lines) if l.startswith(prefix)) for id,prefix,*_ in CASES}
catalog = []
for id, prefix, title, factors, assets in CASES:
    root = ROOT/'cases'/id
    ref = root/'reference'
    ref.mkdir(parents=True, exist_ok=True)
    start = starts[id]
    level = len(prefix) - len(prefix.lstrip('#'))
    end = next((i for i in range(start+1,len(lines)) if i in starts.values() or
                (re.match(r'^#{1,'+str(level)+r'} ',lines[i]))),len(lines))
    (ref/'record.md').write_text(''.join(lines[start:end]))
    public = {'schema_version': 1, 'id': id, 'title': title,
              'status': 'reference-only',
              'readiness_note': 'Historical evidence packaged; clean pre-fix source, fixtures and neutral workload still need a reviewed adapter.'}
    if id.startswith('ftl_') and id != 'ftl_05':
        public['readiness_note'] = 'Requires historical pre-fix Rust/Python source and a native rebuild without embedded PCV markers; current archive binaries are not a fair agent start.'
    if id in SPECS:
        public['status'] = 'pilot-adapter'
        public['readiness_note'] = 'Neutral pinned-source adapter available. Discovery inputs, executable oracle and held-out fixtures still require review before scored release.'
        public['source_revision'] = SPECS[id]['revision']
    dump(root/'case.json',public)
    (root/'task.md').write_text(f'''# {title}

Discover the performance-critical variables (PCVs) of this workload. Locate the
regions whose cost they explain and express the PCVs as computations on state
available at region entry. The cost interface is affine in those expressions;
you do not need to supply its coefficients.

Use code inspection and the measurements allowed by your assigned condition.
Choose experiments that distinguish competing explanations, including changes
to independent inputs. Record your current hypotheses before each measurement,
and submit your revised findings after it. Explain remaining uncertainty.

The task is discovery. Preserve program behavior. Changes for observation and
annotations are allowed; performance fixes are outside this task. Do not replace
a PCV with a computation that re-executes the region or measures its cost.
''')
    inventory = []
    for asset in assets + (['vllm-ditto/examples/cases/common.py'] if id.startswith('ftl_') and id != 'ftl_05' else []):
        src = ARCHIVE/asset
        if src.is_file():
            item = copy(src,ref/'assets'/asset)
            inventory.append(item)
        else:
            raise FileNotFoundError(src)
    dump(ref/'answer.json', {'case': id, 'factors': [
        {'id': f'f{i+1}', 'criterion': criterion} for i,criterion in enumerate(factors)],
        'grading': 'Semantic review against the record and code, not keyword matching. Equivalent expressions and well-supported alternative decompositions count. Historical coefficients are not acceptance thresholds.',
        'scope': 'Observed historical workloads, not an all-input guarantee. Read shared follow-up records for measurement corrections and GPU limits.'})
    dump(ref/'provenance.json', {'record': {'archive_path': 'CASES.md', 'start_line': start+1, 'end_line':end,
         'sha256':hashlib.sha256((ref/'record.md').read_bytes()).hexdigest()}, 'assets': inventory,
         'warning': 'Assets include solved annotations, optimized variants, absolute paths and historical commands. Evaluator evidence only; never execute fix scripts during preparation or expose this directory to agents.'})
    catalog.append(public)

evidence = ROOT/'evaluator'/'evidence'
inventory = [copy(ARCHIVE/p,evidence/p) for p in ['CASES.md','slides/drperf_cases.html','slides/build_deck.py','slides/drperf_cases.pptx']]
dump(evidence/'provenance.json', {'archive_root':str(ARCHIVE),'files':inventory})
dump(ROOT/'catalog.json', {'schema_version':1,'cases':[c['id'] for c in catalog]})
print(f'Packaged {len(catalog)} cases and shared slide/record evidence.')
