"""Drive vLLM's CPU backend so the *output path* (per step, per request) runs
many times with varying state: 12 requests, prompts of four lengths, output
lengths from 4 to 64 tokens, greedy, ignore_eos.

Three phases exercise the three RequestOutputKinds:

  A  FINAL_ONLY (kind=2) -- what LLM.generate() forces (offline_utils._add_request)
  B  CUMULATIVE (kind=0) -- the SamplingParams default; every step rebuilds the
                            whole RequestOutput/CompletionOutput for the request
  C  DELTA      (kind=1) -- streaming-style; only the new tokens/text per step

CUMULATIVE and DELTA are NOT reachable through LLM.generate()/enqueue() (both
funnel through OfflineInferenceMixin._add_request, which overwrites
params.output_kind with FINAL_ONLY), so B and C drive the in-process
LLMEngine directly -- same offline engine, no behaviour changed inside vLLM.

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-out:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export VLLM_CPU_OMP_THREADS_BIND=all
    /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_out.py
"""
import os
import sys
import time

_HF = "/home/ubuntu/drperf/third_party/hf"
if os.path.isdir(_HF):
    os.environ.setdefault("HF_HOME", _HF)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")   # engine in this process
os.environ.setdefault("VLLM_CPU_KVCACHE_SPACE", "1")           # GB
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import perfmark  # noqa: E402

st = perfmark.states(reqs=12, model="facebook/opt-125m", phases="ABC")
REQS, MODEL, PHASES = int(st["reqs"]), str(st["model"]), str(st["phases"])

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402
from vllm.sampling_params import RequestOutputKind  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-out/vllm"
if os.path.abspath(os.path.dirname(vllm.__file__)) != _SRC:
    sys.exit("vllm_run_out.py: vllm imported from %s, not the marked copy %s"
             % (vllm.__file__, _SRC))

llm = LLM(model=MODEL, dtype="bfloat16", enforce_eager=True, max_model_len=512,
          max_num_seqs=16, max_num_batched_tokens=256, seed=0,
          disable_log_stats=True)

# Late attach (`drperf run --late`): DynamoRIO attaches at the first marker, so
# the model load above runs natively.  Stateless on purpose.
with perfmark.region("vllm_attach"):
    pass

BASE = "The quick brown fox jumps over the lazy dog. "
# four prompt lengths (~10, ~20, ~30, ~40 tokens) ...
PROMPTS = [BASE * (1 + (i % 4)) + "Then, number %d:" % i for i in range(REQS)]
# ... and a mix of short and long generations, 4..64
TOKS = [64, 8, 32, 4, 48, 16, 56, 12, 40, 24, 60, 6][:REQS]


def sp(max_tokens, kind):
    return SamplingParams(temperature=0.0, max_tokens=max_tokens, ignore_eos=True,
                          seed=0, output_kind=kind)


# warm-up (still fires markers; just earlier triggers in the trace)
llm.generate([PROMPTS[0]], sp(2, RequestOutputKind.FINAL_ONLY), use_tqdm=False)

results = []

# --- A: LLM.generate, FINAL_ONLY ------------------------------------------
if "A" in PHASES:
    t0 = time.time()
    outs = llm.generate(PROMPTS, [sp(t, RequestOutputKind.FINAL_ONLY) for t in TOKS],
                        use_tqdm=False)
    dt = time.time() - t0
    ntok = sum(len(o.outputs[0].token_ids) for o in outs)
    results.append(("A FINAL_ONLY", len(outs), ntok, dt))
    sample = outs[0].outputs[0].text[:60]

# --- B / C: drive the LLMEngine directly so output_kind survives ----------
def drive(kind, tag, base_id):
    engine = llm.llm_engine
    for i, (prompt, mt) in enumerate(zip(PROMPTS, TOKS)):
        engine.add_request(str(base_id + i), prompt, sp(mt, kind))
    t0 = time.time()
    nout, ntok, nfin = 0, 0, 0
    while engine.has_unfinished_requests():
        for out in engine.step():
            nout += 1
            ntok += len(out.outputs[0].token_ids)
            if out.finished:
                nfin += 1
    dt = time.time() - t0
    results.append(("%s (%d RequestOutputs, %d tok-slots)" % (tag, nout, ntok),
                    nfin, ntok, dt))


if "B" in PHASES:
    drive(RequestOutputKind.CUMULATIVE, "B CUMULATIVE", 1000)
if "C" in PHASES:
    drive(RequestOutputKind.DELTA, "C DELTA", 2000)

for tag, n, ntok, dt in results:
    print("vllm cpu %-52s %2d reqs %5d tok %6.2fs (%.1f tok/s)"
          % (tag, n, ntok, dt, ntok / max(dt, 1e-9)))
print("sample:", repr(sample if "A" in PHASES else ""))
