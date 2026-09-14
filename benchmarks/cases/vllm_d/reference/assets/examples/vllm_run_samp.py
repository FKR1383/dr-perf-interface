"""Drive vLLM's CPU backend so the SAMPLING path is exercised in two modes.

Same prompts in both modes; only the SamplingParams differ:

  mode=greedy     temperature 0                       -> no penalties, no top-k/top-p
  mode=penalised  temperature 0.7, top_k 40, top_p 0.9,
                  repetition 1.2, frequency 0.5, presence 0.3, per-request seed

The markers live in the marked COPY of the vLLM package at
/home/ubuntu/drperf-cases/vllm-cpu-samp/vllm, which must be first on PYTHONPATH:

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-samp:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export VLLM_CPU_OMP_THREADS_BIND=all

Under drperf (from /home/ubuntu/drperf-cases, same env exported):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \
        --max-slots 2097152 -o out/vllm_samp_greedy \
        -- /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_samp.py mode=greedy
    /home/ubuntu/drperf/bin/drperf-dev derive out/vllm_samp_greedy
    /home/ubuntu/drperf/bin/drperf-dev learn  out/vllm_samp_greedy
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

st = perfmark.states(reqs=12, mode="greedy", model="facebook/opt-125m")
REQS, MODE, MODEL = int(st["reqs"]), str(st["mode"]), str(st["model"])
if MODE not in ("greedy", "penalised"):
    sys.exit("vllm_run_samp.py: mode must be greedy or penalised, got %r" % MODE)

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-samp/vllm"
if os.path.abspath(os.path.dirname(vllm.__file__)) != _SRC:
    sys.exit("vllm_run_samp.py: vllm imported from %s, not the marked copy %s"
             % (vllm.__file__, _SRC))

llm = LLM(model=MODEL, dtype="bfloat16", enforce_eager=True, max_model_len=512,
          max_num_seqs=16, max_num_batched_tokens=2048, seed=0, disable_log_stats=True)

# Late attach (`drperf run --late`): DynamoRIO attaches at the first marker, so
# the model load above runs natively.  Stateless on purpose.
with perfmark.region("vllm_attach"):
    pass

base = "The quick brown fox jumps over the lazy dog. "
prompts = [base * (1 + (i % 4)) + "Then, number %d:" % i for i in range(REQS)]
# 16, 32, 48, 64, 80, 96, repeating -- identical in both modes
max_tokens = [16 + 16 * (i % 6) for i in range(REQS)]

if MODE == "greedy":
    params = [SamplingParams(temperature=0.0, max_tokens=max_tokens[i], ignore_eos=True)
              for i in range(REQS)]
else:
    params = [SamplingParams(temperature=0.7, top_k=40, top_p=0.9,
                             repetition_penalty=1.2, frequency_penalty=0.5,
                             presence_penalty=0.3, seed=i,
                             max_tokens=max_tokens[i], ignore_eos=True)
              for i in range(REQS)]

# warm-up outside any measured intent (markers inside vLLM still fire; they are
# just earlier triggers in the trace)
if MODE == "greedy":
    warm = SamplingParams(temperature=0.0, max_tokens=2, ignore_eos=True)
else:
    warm = SamplingParams(temperature=0.7, top_k=40, top_p=0.9,
                          repetition_penalty=1.2, frequency_penalty=0.5,
                          presence_penalty=0.3, seed=0, max_tokens=2, ignore_eos=True)
llm.generate([prompts[0]], warm, use_tqdm=False)

t0 = time.time()
outs = llm.generate(prompts, params, use_tqdm=False)
dt = time.time() - t0
ntok = sum(len(o.outputs[0].token_ids) for o in outs)
print("vllm cpu [%s]: %d requests, %d generated tokens in %.1fs (%.1f tok/s)"
      % (MODE, REQS, ntok, dt, ntok / max(dt, 1e-9)))
print("sample:", repr(outs[0].outputs[0].text[:60]))
