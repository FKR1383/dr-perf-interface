"""Drive vLLM 0.28's CPU backend on the speculative-decoding and
stop-string/logprobs paths, against the marked COPY at
/home/ubuntu/drperf-cases/vllm-cpu-spec.

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-spec:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export VLLM_CPU_OMP_THREADS_BIND=all OMP_NUM_THREADS=8
    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \
        --max-slots 2097152 -o out/vllm_spec_ngram --state k=3,5 \
        -- <python> examples/vllm_run_spec.py mode=spec reqs=8

modes
  spec   ngram speculative decoding, K = `k`, prompt_lookup_max = `lookup`;
         half the prompts repeat (the n-gram lookup hits), half do not.
  plain  the same prompts with no speculative_config (control for `spec`).
  stop   stop strings on every request and logprobs=5 on half of them,
         max_tokens 128 so output_text grows.
  splain the same prompts with neither stop strings nor logprobs (control).
"""
import os
import random
import sys
import time

_HF = "/home/ubuntu/drperf/third_party/hf"
if os.path.isdir(_HF):
    os.environ.setdefault("HF_HOME", _HF)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
os.environ.setdefault("VLLM_CPU_KVCACHE_SPACE", "1")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONHASHSEED", "0")

import perfmark  # noqa: E402

st = perfmark.states(mode="spec", reqs=8, max_tokens=64, k=3, lookup=4, lmin=2,
                     plen=16, pfam=0, lp=1, model="facebook/opt-125m")
MODE = str(st["mode"])
REQS, MAX_TOKENS = int(st["reqs"]), int(st["max_tokens"])
K, LOOKUP, LMIN = int(st["k"]), int(st["lookup"]), int(st["lmin"])
PLEN, PFAM, MODEL = int(st["plen"]), int(st["pfam"]), str(st["model"])
LP = int(st["lp"])   # 0 = no logprobs, 1 = logprobs=5 on odd reqs, 2 = on all

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-spec/vllm"
if os.path.abspath(os.path.dirname(vllm.__file__)) != _SRC:
    sys.exit("vllm_run_spec.py: vllm imported from %s, not %s" % (vllm.__file__, _SRC))

_MAXLEN = max(1024, 64 * (1 + (13 * PLEN + MAX_TOKENS + 64) // 64))
kw = dict(model=MODEL, dtype="bfloat16", enforce_eager=True, max_model_len=_MAXLEN,
          max_num_seqs=16, max_num_batched_tokens=_MAXLEN, seed=0,
          disable_log_stats=True)
if MODE == "spec":
    kw["speculative_config"] = {"method": "ngram", "num_speculative_tokens": K,
                                "prompt_lookup_max": LOOKUP,
                                "prompt_lookup_min": LMIN}


# `drperf run --late` attaches DynamoRIO at the FIRST marker of the run.  vLLM
# fires markers while `LLM(...)` is still building (NgramProposer.__init__ calls
# propose(), and the CPU worker's dummy run goes through the attention marker),
# so without this the attach lands in the middle of the model load and the numba
# JIT of the n-gram kernel (~6.1e9 instructions) is recorded inside `ngram_scan`.
# Turning `perfmark.region` into a null context manager for the duration of the
# load and the warm-up moves the attach to `vllm_attach` below, where it belongs.
class _NullRegion:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


_NULL = _NullRegion()
_REAL_REGION = perfmark.region
perfmark.region = lambda *a, **k: _NULL

# Half the prompts repeat a phrase (so the n-gram suffix match hits), half are
# built from distinct words (so it misses); both families are the same length.
_REP = "the quick brown fox jumps over the lazy dog . "
_WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet "
          "kilo lima mike november oscar papa quebec romeo sierra tango "
          "uniform victor whiskey xray yankee zulu ").split()


_RND = random.Random(7)


def _prompt(i):
    if i % 2 == 0:                      # repeating: n-gram lookup hits
        return "Repeat: " + _REP * PLEN + "the quick brown"
    if PFAM:
        # pfam=1: random numbers, so the suffix n-gram usually does NOT recur
        # and the proposer returns an empty draft for this request.  num_draft
        # then varies independently of num_reqs, which is what separates the
        # per-request from the per-draft-token cost in the fit.
        return "Data %d: " % i + " ".join(str(_RND.randrange(1000))
                                          for _ in range(PLEN * 9))
    n = len(_WORDS)                     # distinct words, but they still recur
    return "List %d: " % i + " ".join(_WORDS[(i * 7 + j * 11) % n]
                                      for j in range(PLEN * 9))


prompts = [_prompt(i) for i in range(REQS)]

def _ntok(i):
    # Stagger the output lengths so the batch drains one request at a time and
    # the per-step states sweep instead of sitting at one point.
    return max(MAX_TOKENS // 4, MAX_TOKENS - (MAX_TOKENS // 12) * i)


if MODE == "stop":
    params = [SamplingParams(temperature=0.0, max_tokens=_ntok(i),
                             ignore_eos=False,
                             stop=["\n\n", "Then"],
                             logprobs=(5 if (LP == 2 or (LP == 1 and i % 2))
                                       else None),
                             min_tokens=(8 if i % 4 == 1 else 0))
              for i in range(REQS)]
elif MODE == "splain":
    params = [SamplingParams(temperature=0.0, max_tokens=_ntok(i),
                             ignore_eos=False)
              for i in range(REQS)]
else:
    # Stagger the output lengths so the batch drains one request at a time and
    # the per-step states (num_reqs, ctx, num_draft) sweep instead of sitting at
    # one point.
    params = [SamplingParams(temperature=0.0,
                             max_tokens=max(8, MAX_TOKENS - 6 * i),
                             ignore_eos=True)
              for i in range(REQS)]


# Build the engine and warm it up with the markers still switched off: the numba
# JIT, the lazy torch/oneDNN paths and the tokenizer caches all run natively.
llm = LLM(**kw)
llm.generate(prompts[:2], SamplingParams(temperature=0.0, max_tokens=8,
                                         ignore_eos=True), use_tqdm=False)

# Markers back on; this is the attach point.  Stateless on purpose: the first
# trigger of a late-attached run is recorded without its states.
perfmark.region = _REAL_REGION
with perfmark.region("vllm_attach"):
    pass

t0 = time.time()
outs = llm.generate(prompts, params, use_tqdm=False)
dt = time.time() - t0
ntok = sum(len(o.outputs[0].token_ids) for o in outs)
print("vllm %s: %d requests, %d generated tokens in %.1fs (%.1f tok/s)"
      % (MODE, REQS, ntok, dt, ntok / max(dt, 1e-9)))
if os.environ.get("SPEC_DUMP"):
    import hashlib
    import json
    recs = [{"i": i, "ids": list(o.outputs[0].token_ids), "text": o.outputs[0].text,
             "finish": o.outputs[0].finish_reason,
             "stop": o.outputs[0].stop_reason,
             "clp": o.outputs[0].cumulative_logprob,
             "lp": (None if o.outputs[0].logprobs is None else
                    [sorted((int(t), round(float(l.logprob), 6), l.rank,
                             l.decoded_token) for t, l in d.items())
                     for d in o.outputs[0].logprobs])}
            for i, o in enumerate(outs)]
    blob = json.dumps(recs, sort_keys=True)
    open(os.environ["SPEC_DUMP"], "w").write(blob)
    print("dump sha256:", hashlib.sha256(blob.encode()).hexdigest())
print("sample:", repr(outs[0].outputs[0].text[:60]))
