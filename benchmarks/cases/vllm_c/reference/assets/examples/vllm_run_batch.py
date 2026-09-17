"""Drive vLLM's CPU backend with more requests than slots, so the persistent
batch churns: requests queue, are admitted, finish at staggered steps and are
replaced, which makes num_new / num_finished / condense vary every few steps.

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-batch:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export VLLM_CPU_OMP_THREADS_BIND=all
    /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_batch.py [reqs=24]

Under drperf (from /home/ubuntu/drperf-cases, same env exported):

    /home/ubuntu/drperf/bin/drperf-dev run --blocks -q --late --threads 8 --repeat 1 \
        --max-slots 2097152 -o out/vllm_batch \
        -- /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_batch.py
    /home/ubuntu/drperf/bin/drperf-dev derive out/vllm_batch
    /home/ubuntu/drperf/bin/drperf-dev learn out/vllm_batch
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

st = perfmark.states(reqs=24, seqs=8, plen=1, model="facebook/opt-125m")
REQS, SEQS, PLEN, MODEL = int(st["reqs"]), int(st["seqs"]), int(st["plen"]), str(st["model"])

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-batch/vllm"
if not os.path.abspath(os.path.dirname(vllm.__file__)) == _SRC:
    sys.exit("vllm_run_batch.py: vllm imported from %s, not the marked copy %s "
             "(put %s first on PYTHONPATH)" % (vllm.__file__, _SRC, os.path.dirname(_SRC)))

llm = LLM(model=MODEL, dtype="bfloat16", enforce_eager=True, max_model_len=512,
          max_num_seqs=SEQS, max_num_batched_tokens=256, seed=0, disable_log_stats=True)

# Late attach (`drperf run --late`): DynamoRIO attaches at the first marker, so
# the model load above runs natively.
with perfmark.region("vllm_attach"):
    pass

# 4 prompt lengths (roughly 12, 23, 34, 45 tokens at plen=1; x PLEN), output lengths spread
# 4..40 in steps of 6 so that finishes are staggered across steps.
base = "The quick brown fox jumps over the lazy dog. "
prompts = [base * (PLEN * (1 + (i % 4))) + "Then, number %d:" % i for i in range(REQS)]
params = [SamplingParams(temperature=0.0, max_tokens=4 + 6 * (i % 7), ignore_eos=True)
          for i in range(REQS)]

# warm-up outside any measured intent (markers inside vLLM still fire; they are
# just earlier triggers in the trace)
llm.generate([prompts[0]], SamplingParams(temperature=0.0, max_tokens=2, ignore_eos=True),
             use_tqdm=False)

t0 = time.time()
outs = llm.generate(prompts, params, use_tqdm=False)
dt = time.time() - t0
ntok = sum(len(o.outputs[0].token_ids) for o in outs)
print("vllm cpu batch: %d requests (max_num_seqs=%d), %d generated tokens in %.1fs (%.1f tok/s)"
      % (REQS, SEQS, ntok, dt, ntok / max(dt, 1e-9)))
print("sample:", repr(outs[0].outputs[0].text[:60]))
