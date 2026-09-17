"""Insert perfmark regions around vLLM's per-step KV-cache / prefix-cache paths.

    python examples/vllm_mark_kv.py /home/ubuntu/drperf-cases/vllm-cpu-src [--undo]

The argument is the tree ROOT, i.e. the directory that *contains* the `vllm`
package (the entry that goes first on PYTHONPATH), exactly like
/home/ubuntu/drperf/examples/vllm_cpu/mark.py.

Each marked function gets its whole body wrapped in

    with perfmark.region("<name>", <state>=<int expr>, ...):

so that `drperf run --model` can analyse its structure and capture its free
variables.  Every state expression is evaluated at function entry and is
read-only: no vLLM behaviour changes.  Idempotent; `--undo` restores the files
from the `.kvorig` copies it keeps (a suffix distinct from mark.py's `.orig`
so the two marker scripts can coexist on the same tree).

`wrap_method` is copied from drperf's examples/vllm_cpu/mark.py and generalised
in one place only: the scope may be a class *or* a module-level `def`, so that
the closure `request_block_hasher` nested inside `get_request_block_hasher`
can be marked too.
"""
import os
import re
import shutil
import sys

# file, scope ("class X" or "def X" at column 0), function, region name,
# declared states (integer keywords; all of them form the aggregation key and
# the cost formula is derived in all of them; at most four per region)
MARKS = [
    # --- KVCacheManager: admission / allocation / release -------------------
    # get_computed_blocks -> coordinator.find_longest_cache_hit: one dict lookup
    # per hash block of the prompt.  KVCacheManager has no `self.block_size`
    # (only kv_cache_spec.block_size, per group), so the prompt block count is
    # taken from len(request.block_hashes), which is exactly the loop bound of
    # find_longest_cache_hit and is already populated at entry (Request.__init__
    # / update_block_hashes ran before the scheduler calls this).
    ("vllm/v1/core/kv_cache_manager.py", "class KVCacheManager", "get_computed_blocks",
     "kv_get_computed_blocks",
     "num_tokens=request.num_tokens, num_hashes=len(request.block_hashes)"),
    ("vllm/v1/core/kv_cache_manager.py", "class KVCacheManager", "allocate_slots",
     "kv_allocate_slots",
     "num_new_tokens=num_new_tokens, num_computed=request.num_computed_tokens"),
    # free(request) only receives the request; the blocks it is about to release
    # live in the per-group single-type managers.  `.get(..., ())` keeps the
    # read non-mutating (req_to_blocks is a defaultdict).
    ("vllm/v1/core/kv_cache_manager.py", "class KVCacheManager", "free", "kv_free",
     "num_blocks=len(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())),"
     " num_tokens=request.num_tokens"),

    # --- BlockPool: hash-map insert per newly full block --------------------
    ("vllm/v1/core/block_pool.py", "class BlockPool", "cache_full_blocks",
     "kv_cache_full_blocks",
     "num_new=num_full_blocks - num_cached_blocks, num_cached=num_cached_blocks"),

    # --- prefix-cache hashing, once per appended output token ---------------
    # Request.append_output_token_ids -> Request.update_block_hashes ->
    # this closure.  It hashes (num_tokens // hash_block_size) - num_hashes
    # new full blocks, so both bounds are declared.
    ("vllm/v1/core/kv_cache_utils.py", "def get_request_block_hasher", "request_block_hasher",
     "kv_block_hasher",
     "num_hashes=len(request.block_hashes), num_tokens=request.num_tokens"),

    # --- shared-prefix scan, once per scheduler step ------------------------
    # scheduler.py calls this on running[0]; the concrete implementation lives
    # in FullAttentionManager (the base class method is abstract).
    ("vllm/v1/core/single_type_kv_cache_manager.py", "class FullAttentionManager",
     "get_num_common_prefix_blocks", "kv_common_prefix_blocks",
     "num_running=len(self.req_to_blocks),"
     " num_blocks=len(self.req_to_blocks.get(running_request_id, ()))"),

    # --- detokenisation, once per request per step --------------------------
    # concrete update() is on BaseIncrementalDetokenizer; `output_text +=` makes
    # the current text length a cost driver, so it is declared as well.
    ("vllm/v1/engine/detokenizer.py", "class BaseIncrementalDetokenizer", "update",
     "detokenize_update",
     "num_new=len(new_token_ids), text_len=len(self.output_text)"),

    # OutputProcessor.process_outputs / make_request_output are marked by the
    # other agent's script -- deliberately not repeated here.
]

ORIG_SUFFIX = ".kvorig"


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
    raise SystemExit("vllm_mark_kv.py: %s / %s not found (region %s)" % (scope, method, region))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
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
            raise SystemExit("vllm_mark_kv.py: no such file: %s" % full)
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
