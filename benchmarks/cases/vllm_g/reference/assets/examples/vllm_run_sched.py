"""Drive vLLM's CPU backend so the SCHEDULER's waiting queue, preemption path
and chunked-prefill accounting are exercised.  Marked copy:
/home/ubuntu/drperf-cases/vllm-cpu-sched (examples/vllm_mark_sched.py).

    export PYTHONPATH=/home/ubuntu/drperf-cases/vllm-cpu-sched:/home/ubuntu/drperf/perfmark/python:/home/ubuntu/drperf/build
    export VLLM_CPU_OMP_THREADS_BIND=all OMP_NUM_THREADS=8
    /home/ubuntu/drperf/third_party/vllm-cpu/.venv/bin/python examples/vllm_run_sched.py mode=saturation

Modes (`mode=` state, also settable with `drperf run --state mode=...`):

  saturation  48 short requests through max_num_seqs=8: at every step the
              waiting queue holds up to 40 requests that cannot be admitted.
  priority    20 requests with scheduling_policy="priority", per-request
              priorities, a 44-block (block_size 16) KV cache and no prefix
              cache, so `allocate_slots` fails for running requests and the
              max()/index() preemption path runs (~15 preemptions).
  chunked     6 requests with 1.0k-1.6k token prompts, max_model_len=2048
              and max_num_batched_tokens=128, so every prompt is spread over
              ~10 chunked-prefill steps.
"""
import os
import sys
import time

_HF = "/home/ubuntu/drperf/third_party/hf"
if os.path.isdir(_HF):
    os.environ.setdefault("HF_HOME", _HF)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import perfmark  # noqa: E402

st = perfmark.states(mode="saturation", reqs=0, max_num_seqs=0, blocks=0, dump=0,
                     model="facebook/opt-125m")
MODE = str(st["mode"])
MODEL = str(st["model"])
DUMP = int(st["dump"])

BASE = "The quick brown fox jumps over the lazy dog. "

if MODE == "saturation":
    REQS = int(st["reqs"]) or 48
    MAX_NUM_SEQS = int(st["max_num_seqs"]) or 8
    BLOCKS = int(st["blocks"]) or None
    BLOCK_SIZE = None
    PREFIX_CACHING = None
    MAX_MODEL_LEN, MAX_BATCHED, POLICY = 256, 128, "fcfs"
    prompts = [BASE * (1 + (i % 4)) + "Then, number %d:" % i for i in range(REQS)]
    max_tokens = [8 + 8 * (i % 4) for i in range(REQS)]         # 8..32
    priorities = None
elif MODE == "priority":
    REQS = int(st["reqs"]) or 20
    MAX_NUM_SEQS = int(st["max_num_seqs"]) or 12
    BLOCKS = int(st["blocks"]) or 44
    BLOCK_SIZE = 16          # the CPU default of 128 puts preemption out of reach
    PREFIX_CACHING = False   # with the prefix cache on, freed blocks are reusable
                             # and allocate_slots almost never fails
    MAX_MODEL_LEN, MAX_BATCHED, POLICY = 512, 512, "priority"
    # 40..60-token prompts all fit; every 16 decoded tokens each running
    # request needs one more block, so running requests are preempted
    # mid-decode through max(self.running) / self.running.index().
    prompts = [BASE * (4 + (i % 3)) + "Then, number %d:" % i for i in range(REQS)]
    max_tokens = [48 + 16 * (i % 3) for i in range(REQS)]
    priorities = [(i * 7) % 5 for i in range(REQS)]              # 0..4, interleaved
elif MODE == "chunked":
    REQS = int(st["reqs"]) or 6
    MAX_NUM_SEQS = int(st["max_num_seqs"]) or 8
    BLOCKS = int(st["blocks"]) or None
    BLOCK_SIZE = None
    PREFIX_CACHING = None
    MAX_MODEL_LEN, MAX_BATCHED, POLICY = 2048, 128, "fcfs"   # opt-125m caps at 2048
    # 1.0k..1.6k tokens: BASE is ~10.25 tokens.
    # a distinct leading phrase per request so prompts share no long prefix
    prompts = ["Request %d says: " % i + BASE * (98 + 12 * i)
               + "Then, number %d:" % i for i in range(REQS)]
    max_tokens = [8 for _ in range(REQS)]
    priorities = None
else:
    sys.exit("vllm_run_sched.py: unknown mode %r" % MODE)

os.environ.setdefault("VLLM_CPU_KVCACHE_SPACE", "1")   # GiB, integer only

import vllm  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

_SRC = "/home/ubuntu/drperf-cases/vllm-cpu-sched/vllm"
if os.path.abspath(os.path.dirname(vllm.__file__)) != _SRC:
    sys.exit("vllm_run_sched.py: vllm imported from %s, not the marked copy %s"
             % (vllm.__file__, _SRC))

llm = LLM(model=MODEL, dtype="bfloat16", enforce_eager=True,
          max_model_len=MAX_MODEL_LEN, max_num_seqs=MAX_NUM_SEQS,
          max_num_batched_tokens=MAX_BATCHED, scheduling_policy=POLICY,
          num_gpu_blocks_override=BLOCKS, block_size=BLOCK_SIZE,
          enable_prefix_caching=PREFIX_CACHING,
          seed=0, disable_log_stats=True)

params = [SamplingParams(temperature=0.0, max_tokens=t, ignore_eos=True) for t in max_tokens]

# warm-up outside any measured intent
llm.generate([prompts[0]], SamplingParams(temperature=0.0, max_tokens=2, ignore_eos=True),
             use_tqdm=False)

# Late attach (`drperf run --late`): stateless, so the model load runs natively.
with perfmark.region("vllm_attach"):
    pass

t0 = time.time()
if priorities is not None:
    outs = llm.generate(prompts, params, use_tqdm=False, priority=priorities)
else:
    outs = llm.generate(prompts, params, use_tqdm=False)
dt = time.time() - t0

ntok = sum(len(o.outputs[0].token_ids) for o in outs)
nprompt = sum(len(o.prompt_token_ids) for o in outs)
print("vllm sched[%s]: %d reqs, prompt %d tok (max %d), gen %d tok in %.1fs (%.1f tok/s)"
      % (MODE, len(outs), nprompt, max(len(o.prompt_token_ids) for o in outs), ntok, dt,
         ntok / max(dt, 1e-9)))
print("sample:", repr(outs[0].outputs[0].text[:60]))
if DUMP:
    import hashlib
    h = hashlib.sha256()
    for o in sorted(outs, key=lambda o: int(o.request_id)):
        h.update(("%s|%s|%r\n" % (o.request_id, list(o.outputs[0].token_ids),
                                  o.outputs[0].text)).encode())
    print("outputs-sha256:", h.hexdigest())
