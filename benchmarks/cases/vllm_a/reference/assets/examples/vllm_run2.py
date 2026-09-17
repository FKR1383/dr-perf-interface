"""Drive vLLM's CPU backend so the KV-cache / prefix-cache paths trigger many
times with varying state.

Derived from examples/vllm_run.py.  Differences that matter for the markers
added by examples/vllm_mark_kv.py:

  * every prompt starts with the SAME long system prompt, so the prefix cache
    actually hits (get_computed_blocks / find_longest_cache_hit) and the
    running requests share blocks (get_num_common_prefix_blocks > 0);
  * prompt lengths vary over roughly 64..600 tokens, so the number of hash
    blocks per request, the cache-hit length and the block-pool inserts vary;
  * max_tokens varies over 8..40, so blocks keep filling during decode
    (cache_full_blocks / the per-token block hasher) and requests finish at
    different steps (free / detokenizer with different text lengths);
  * block_size=16 instead of the CPU default of 128: with 128-token blocks a
    600-token prompt is only 4 blocks, so the per-block loops barely vary
    (cache_full_blocks fired 6x with num_new==1); at 16 the same workload gives
    num_blocks 4..40 and num_new 1..12.  It is a config knob, not a code change,
    and the generated text is byte-identical either way;
  * everything is deterministic: greedy sampling, fixed seed, ignore_eos.

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-src:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export OMP_NUM_THREADS=8 VLLM_CPU_OMP_THREADS_BIND=all
    /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run2.py [reqs=12] [max_tokens=40]

Under drperf (from /home/ubuntu/drperf-cases, same env exported):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \\
        --max-slots 2097152 -o out/vllm_kv \\
        -- /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run2.py
"""
import os
import sys
import time

_HF = "/home/ubuntu/drperf/third_party/hf"
if os.path.isdir(_HF):
    os.environ.setdefault("HF_HOME", _HF)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")   # keep the engine in this process
os.environ.setdefault("VLLM_CPU_KVCACHE_SPACE", "1")             # GB
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import perfmark  # noqa: E402

st = perfmark.states(reqs=12, max_tokens=40, min_tokens=8, block_size=16,
                     model="facebook/opt-125m")
REQS = int(st["reqs"])
MAX_TOKENS = int(st["max_tokens"])
MIN_TOKENS = int(st["min_tokens"])
BLOCK_SIZE = int(st["block_size"])
MODEL = str(st["model"])

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-src/vllm"
if not os.path.abspath(os.path.dirname(vllm.__file__)) == _SRC:
    sys.exit("vllm_run2.py: vllm imported from %s, not the marked copy %s (put %s first on PYTHONPATH)"
             % (vllm.__file__, _SRC, os.path.dirname(_SRC)))

llm = LLM(model=MODEL, dtype="bfloat16", enforce_eager=True, max_model_len=1024,
          max_num_seqs=16, max_num_batched_tokens=1024, seed=0,
          enable_prefix_caching=True, block_size=BLOCK_SIZE,
          disable_log_stats=True)

# Late-attach anchor: drperf --late starts sampling at the first trigger, so the
# model load above is excluded.  Must be stateless.
with perfmark.region("vllm_attach"):
    pass

# ---------------------------------------------------------------- prompts ---
# A shared system prompt (many blocks long) followed by a per-request body of
# growing length.  Same text prefix => same token prefix => prefix-cache hits.
SYSTEM = (
    "You are a careful assistant running on a CPU backend. "
    "Answer briefly, in plain words, and never invent facts. "
    "Keep the tone neutral and the sentences short. "
    "If a question is ambiguous, state the assumption you make. "
    "Always finish with a single concluding sentence. "
)
BODY = ("The quick brown fox jumps over the lazy dog near the quiet river bank. "
        "A slow grey heron watches the water and waits for the evening light. ")

# ~50-token shared prefix + 0..18 body repeats (~30 tokens each) spans the
# prompt length over roughly 64..600 tokens; requests i and i+6 share the whole
# body as well, so the prefix-cache hit length varies too.
REPEATS = [0, 2, 5, 8, 12, 18]
prompts = [SYSTEM + BODY * REPEATS[i % len(REPEATS)] + "Question %d: what happened next?" % i
           for i in range(REQS)]
# max_tokens cycles over MIN_TOKENS..MAX_TOKENS
span = max(MAX_TOKENS - MIN_TOKENS, 1)
params = [SamplingParams(temperature=0.0, seed=0, ignore_eos=True,
                         max_tokens=MIN_TOKENS + (i * span) // max(REQS - 1, 1))
          for i in range(REQS)]

tok = llm.get_tokenizer()
plens = [len(tok(p).input_ids) for p in prompts]
print("prompt tokens: %s" % plens)
print("max_tokens:    %s" % [p.max_tokens for p in params])

# warm-up outside the measured intent (markers still fire; they are just
# earlier triggers in the trace)
llm.generate([prompts[0]], SamplingParams(temperature=0.0, max_tokens=2, ignore_eos=True),
             use_tqdm=False)

t0 = time.time()
outs = llm.generate(prompts, params, use_tqdm=False)
dt = time.time() - t0
ntok = sum(len(o.outputs[0].token_ids) for o in outs)
print("vllm cpu kv: %d requests, %d prompt tokens, %d generated tokens in %.1fs (%.1f tok/s)"
      % (REQS, sum(plens), ntok, dt, ntok / max(dt, 1e-9)))
print("sample:", repr(outs[0].outputs[0].text[:60]))
