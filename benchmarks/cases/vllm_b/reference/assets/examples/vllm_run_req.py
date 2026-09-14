"""Drive vLLM's CPU backend so that the PER-REQUEST lifecycle (admission and
teardown), not decode, dominates the run.

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-req:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export VLLM_CPU_OMP_THREADS_BIND=all
    /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_req.py

Under drperf (from /home/ubuntu/drperf-cases, same env exported):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \\
        --max-slots 2097152 -o out/vllm_req \\
        -- /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_req.py
    /home/ubuntu/drperf/bin/drperf-dev derive out/vllm_req
    /home/ubuntu/drperf/bin/drperf-dev learn  out/vllm_req

Design: 16 requests whose prompts run from ~16 to ~600 tokens (the same sentence
repeated), max_tokens=4 so only four decode steps per request follow a prefill,
max_num_seqs=16 so all 16 are admitted in one go and torn down close together.
The SAME 16 prompts are then submitted a second time, so that anything cached
across `generate()` calls (tokenizer, prefix cache) shows up as a difference
between the two passes rather than being invisible.
"""
import os
import sys
import time

_HF = "/home/ubuntu/drperf/third_party/hf"
if os.path.isdir(_HF):
    os.environ.setdefault("HF_HOME", _HF)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")   # keep the engine in this process
os.environ.setdefault("VLLM_CPU_KVCACHE_SPACE", "1")           # GB
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import perfmark  # noqa: E402

# `passes` lists the prompt count of each generate() call.  The default "16,16"
# is the two identical passes described above; pass e.g. passes=16,16,4,8,12 to
# give `add_requests_loop`'s num_prompts more than one value so derive can fit
# it (out/vllm_req_n).
st = perfmark.states(reqs=16, max_tokens=4, passes="16,16", model="facebook/opt-125m")
REQS, MAX_TOKENS, MODEL = int(st["reqs"]), int(st["max_tokens"]), str(st["model"])
PASSES = [int(x) for x in str(st["passes"]).split(",") if x.strip()]

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-req/vllm"
if os.path.abspath(os.path.dirname(vllm.__file__)) != _SRC:
    sys.exit("vllm_run_req.py: vllm imported from %s, not the marked copy %s "
             "(put %s first on PYTHONPATH)"
             % (vllm.__file__, _SRC, os.path.dirname(_SRC)))

llm = LLM(model=MODEL, dtype="bfloat16", enforce_eager=True, max_model_len=768,
          max_num_seqs=16, max_num_batched_tokens=1024, seed=0,
          disable_log_stats=True)

# Late attach (`drperf run --late`): DynamoRIO attaches at the first marker, so
# the model load above runs natively.  Stateless on purpose: the first trigger
# of a late-attached run is recorded without its states.
with perfmark.region("vllm_attach"):
    pass

# ~9 tokens per repetition of `SENT` for opt-125m, plus BOS; i reps -> roughly
# 16 .. 600 prompt tokens over the 16 requests.
SENT = "The quick brown fox jumps over the lazy dog. "
REPS = [1, 2, 4, 6, 9, 12, 16, 20, 25, 30, 36, 42, 48, 54, 60, 66]
prompts = [SENT * REPS[i % len(REPS)] for i in range(REQS)]
params = SamplingParams(temperature=0.0, max_tokens=MAX_TOKENS, ignore_eos=True, seed=0)

# Pass 2 repeats pass 1 over the SAME prompts: anything cached across
# generate() calls (tokenizer, prefix cache) shows up as a difference between
# the two passes rather than being invisible.
outs = []
times = []
for n in PASSES:
    t = time.time()
    # evenly spread subset, so shorter passes keep the same length distribution
    sub = [prompts[(i * REQS) // n] for i in range(n)]
    outs.append(llm.generate(sub, params, use_tqdm=False))
    times.append(time.time() - t)

ptok = [len(o.prompt_token_ids) for o in outs[0]]
ntok = sum(len(o.outputs[0].token_ids) for o in outs[0])
print("vllm cpu req: %d requests, prompt tokens %d..%d (total %d), %d generated tokens"
      % (len(outs[0]), min(ptok), max(ptok), sum(ptok), ntok))
print("passes " + ", ".join("%d prompts %.2fs" % (n, t) for n, t in zip(PASSES, times))
      + "   total %.2fs" % sum(times))
print("sample:", repr(outs[0][0].outputs[0].text[:60]))
