"""Insert perfmark regions around vLLM's PER-REQUEST lifecycle (admission and
teardown), i.e. everything outside the per-step engine loop.

    python examples/vllm_mark_req.py /home/ubuntu/drperf-cases/vllm-cpu-req [--undo]

The argument is the tree ROOT, i.e. the directory that *contains* the `vllm`
package (the entry that goes first on PYTHONPATH), exactly like
/home/ubuntu/drperf/examples/vllm_cpu/mark.py.

Every marked function gets its whole body wrapped in

    with perfmark.region("<name>", <state>=<int expr>, ...):

Each state expression is evaluated at function entry, is read-only, and is at
most four per region: no vLLM behaviour changes.  Idempotent; `--undo` restores
the files from the `.reqorig` copies it keeps (a suffix distinct from mark.py's
`.orig` and vllm_mark_kv.py's `.kvorig` so the marker scripts can coexist).

`wrap_method` is copied from drperf's examples/vllm_cpu/mark.py, with the same
one generalisation vllm_mark_kv.py makes (the scope may be a class *or* a
module-level `def`).

Call graph of the marked regions for the offline `LLM.generate()` front end
(vLLM 0.28, V1 engine, in-process EngineCore):

  add_requests_loop      OfflineInferenceMixin._render_and_add_requests
   |- render_prompt       OfflineInferenceMixin._preprocess_cmpl_one  (tokenizer)
   `- engine_add_request  LLMEngine.add_request
       |- process_inputs   InputProcessor.process_inputs (validate, clone params,
       |                                                  build EngineCoreRequest)
       `- core_add_request EngineCore.add_request  -- called via InprocClient,
           |                                          preceded by preprocess_add_request
           `- sched_add_request Scheduler.add_request
  (teardown, inside the step loop's update_from_output or on abort)
  sched_finish_requests   Scheduler.finish_requests
  sched_free_request      Scheduler._free_request
   `- kv_free              KVCacheManager.free
"""
import os
import re
import shutil
import sys

# The prompt handed to LLMEngine.add_request / InputProcessor.process_inputs is
# an already-rendered EngineInput dict in vLLM 0.28; fall back to the raw string
# length when it is not (deprecated raw-prompt path).
_NTOK = (
    'num_tokens=(len(prompt.get("prompt_token_ids") or ()) '
    'if isinstance(prompt, dict) else (len(prompt) if isinstance(prompt, str) else 0))'
)
# Blocks currently booked for a request, read without mutating the defaultdict.
_NBLK = (
    'num_blocks=len(%s.coordinator.single_type_managers[0]'
    '.req_to_blocks.get(request.request_id, ()))'
)

# file, scope ("class X" or "def X" at column 0), function, region name,
# declared states (integer keywords; all of them form the aggregation key and
# the cost formula is derived in all of them; at most four per region)
MARKS = [
    # --- offline front end: the per-prompt loop and the tokenizer ----------
    ("vllm/entrypoints/offline_utils.py", "class OfflineInferenceMixin",
     "_render_and_add_requests", "add_requests_loop",
     "num_prompts=len(params)"),
    ("vllm/entrypoints/offline_utils.py", "class OfflineInferenceMixin",
     "_preprocess_cmpl_one", "render_prompt",
     'prompt_chars=(len(prompt) if isinstance(prompt, str) else 0)'),

    # --- engine front end --------------------------------------------------
    ("vllm/v1/engine/llm_engine.py", "class LLMEngine", "add_request",
     "engine_add_request", _NTOK),
    ("vllm/v1/engine/input_processor.py", "class InputProcessor", "process_inputs",
     "process_inputs", _NTOK),

    # --- EngineCore side: Request construction and admission ---------------
    # preprocess_add_request is where Request.from_engine_core_request runs.
    ("vllm/v1/engine/core.py", "class EngineCore", "preprocess_add_request",
     "core_preprocess_add",
     "num_prompt=len(request.prompt_token_ids or ())"),
    # NB: `num_blocks` -- Request.__init__ used to hash every full block of the
    # prompt (update_block_hashes), so its cost is a staircase in the prompt
    # length, not a line.  The hash granularity is not a constructor argument;
    # `get_request_block_hasher` publishes it on the hasher it returns.
    ("vllm/v1/request.py", "class Request", "__init__", "request_init",
     'num_prompt=(len(prompt_token_ids) if prompt_token_ids is not None else 0), num_blocks=(len(prompt_token_ids) // getattr(block_hasher, "hash_block_size", 0) if prompt_token_ids and getattr(block_hasher, "hash_block_size", 0) else 0)'),
    ("vllm/v1/engine/core.py", "class EngineCore", "add_request", "core_add_request",
     "num_tokens=request.num_tokens, num_prompt=request.num_prompt_tokens"),
    ("vllm/v1/core/sched/scheduler.py", "class Scheduler", "add_request",
     "sched_add_request",
     "waiting=len(self.waiting), running=len(self.running), num_reqs=len(self.requests)"),

    # --- teardown ----------------------------------------------------------
    ("vllm/v1/core/sched/scheduler.py", "class Scheduler", "finish_requests",
     "sched_finish_requests",
     # NB: never consume `request_ids` -- it may be any iterable, so only a
     # sized container is measured; a generator reports 0 and is left intact.
     "running=len(self.running), num_ids=(1 if isinstance(request_ids, str) else"
     " (len(self.requests) if request_ids is None else"
     ' (len(request_ids) if hasattr(request_ids, "__len__") else 0)))'),
    ("vllm/v1/core/sched/scheduler.py", "class Scheduler", "_free_request",
     "sched_free_request",
     "running=len(self.running), " + (_NBLK % "self.kv_cache_manager") +
     ", num_tokens=request.num_tokens"),
    ("vllm/v1/core/kv_cache_manager.py", "class KVCacheManager", "free", "kv_free",
     (_NBLK % "self") + ", num_tokens=request.num_tokens"),
]

ORIG_SUFFIX = ".reqorig"


def wrap_method(src, scope, method, region, state):
    """Wrap the body of `method` (defined at indent 4 inside `scope`) in a region.

    `scope` is a column-0 definition line prefix, e.g. "class KVCacheManager"
    or "def get_request_block_hasher".
    """
    lines = src.splitlines(True)
    scope_re = re.compile(r"%s\b" % re.escape(scope))
    other_re = re.compile(r"(?:class|def)\s+\w")
    in_scope = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if scope_re.match(line):
            in_scope = True
        elif other_re.match(line):
            in_scope = False
        if in_scope and re.match(r"    def %s\(" % re.escape(method), line):
            # find end of signature (line ending with ':' at nesting depth 0)
            j = i
            depth = 0
            while True:
                depth += lines[j].count("(") - lines[j].count(")")
                if depth <= 0 and lines[j].rstrip().endswith(":"):
                    break
                j += 1
            body_start = j + 1
            # skip a docstring
            k = body_start
            if lines[k].lstrip().startswith(('"""', "'''")):
                q = lines[k].lstrip()[:3]
                if lines[k].count(q) >= 2 and len(lines[k].strip()) > 3:
                    k += 1
                else:
                    k += 1
                    while q not in lines[k]:
                        k += 1
                    k += 1
            # body ends at the next line with indentation <= 4 that is not blank
            end = k
            while end < len(lines):
                l = lines[end]
                if l.strip() and (len(l) - len(l.lstrip())) <= 4:
                    break
                end += 1
            if any("perfmark.region(\"%s\"" % region in l for l in lines[k:end]):
                return src, False
            head = "        with perfmark.region(\"%s\", %s):\n" % (region, state)
            body = ["    " + l if l.strip() else l for l in lines[k:end]]
            lines[k:end] = [head] + body
            out = "".join(lines)
            if "import perfmark\n" not in out:
                # after the first block of imports
                m = re.search(r"^(?:from|import) .*\n", out, re.M)
                pos = m.start() if m else 0
                out = out[:pos] + "import perfmark\n" + out[pos:]
            return out, True
        i += 1
    raise SystemExit("vllm_mark_req.py: %s / %s not found (region %s)" % (scope, method, region))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        raise SystemExit("usage: vllm_mark_req.py <tree root containing vllm/> [--undo]")
    root = args[0]
    undo = "--undo" in sys.argv
    seen = []
    for path, scope, method, region, state in MARKS:
        full = os.path.join(root, path)
        orig = full + ORIG_SUFFIX
        if undo:
            if path not in seen and os.path.exists(orig):
                shutil.move(orig, full)
                print("restored", path)
            seen.append(path)
            continue
        if not os.path.exists(full):
            raise SystemExit("vllm_mark_req.py: no such file: %s" % full)
        if not os.path.exists(orig):
            shutil.copy(full, orig)
        src = open(full).read()
        out, changed = wrap_method(src, scope, method, region, state)
        if changed:
            open(full, "w").write(out)
            print("marked %s / %s -> region %s (%s)" % (scope, method, region, state))
        else:
            print("already marked %s / %s" % (scope, method))


if __name__ == "__main__":
    main()
