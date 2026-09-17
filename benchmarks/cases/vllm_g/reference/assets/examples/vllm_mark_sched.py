"""Insert perfmark regions around vLLM's SCHEDULING paths: the waiting-queue
admission loop, the preemption retry, the request queues, and the per-step
chunked-prefill accounting.

    python examples/vllm_mark_sched.py /home/ubuntu/drperf-cases/vllm-cpu-sched [--undo]

The argument is the tree ROOT (the directory containing the `vllm` package).
Whole methods are wrapped with `wrap_method` (same shape as
examples/vllm_mark_req.py); four regions inside `Scheduler.schedule` are
inserted by anchor, because the interesting bodies are loop bodies, not
methods.  Every state expression is read-only and evaluated at region entry.
Idempotent; `--undo` restores the `.schedorig` copies.
"""
import os
import re
import shutil
import sys

ORIG_SUFFIX = ".schedorig"

# ---------------------------------------------------------------- whole methods
MARKS = [
    # --- the request queues: peek/pop/prepend/remove, keyed by queue length ---
    ("vllm/v1/core/sched/request_queue.py", "class FCFSRequestQueue", "add_request",
     "fcfs_add", "queue_len=len(self)"),
    ("vllm/v1/core/sched/request_queue.py", "class FCFSRequestQueue", "pop_request",
     "fcfs_pop", "queue_len=len(self)"),
    ("vllm/v1/core/sched/request_queue.py", "class FCFSRequestQueue", "peek_request",
     "fcfs_peek", "queue_len=len(self)"),
    ("vllm/v1/core/sched/request_queue.py", "class FCFSRequestQueue", "prepend_request",
     "fcfs_prepend", "queue_len=len(self)"),
    ("vllm/v1/core/sched/request_queue.py", "class FCFSRequestQueue", "prepend_requests",
     "fcfs_prepend_many", "queue_len=len(self), n=len(requests)"),
    ("vllm/v1/core/sched/request_queue.py", "class FCFSRequestQueue", "remove_request",
     "fcfs_remove", "queue_len=len(self)"),
    ("vllm/v1/core/sched/request_queue.py", "class PriorityRequestQueue", "add_request",
     "prio_add", "queue_len=len(self._heap)"),
    ("vllm/v1/core/sched/request_queue.py", "class PriorityRequestQueue", "pop_request",
     "prio_pop", "queue_len=len(self._heap)"),
    ("vllm/v1/core/sched/request_queue.py", "class PriorityRequestQueue", "peek_request",
     "prio_peek", "queue_len=len(self._heap)"),
    ("vllm/v1/core/sched/request_queue.py", "class PriorityRequestQueue", "prepend_request",
     "prio_prepend", "queue_len=len(self._heap)"),
    ("vllm/v1/core/sched/request_queue.py", "class PriorityRequestQueue", "prepend_requests",
     "prio_prepend_many", "queue_len=len(self._heap), n=len(requests)"),
    ("vllm/v1/core/sched/request_queue.py", "class PriorityRequestQueue", "remove_request",
     "prio_remove", "queue_len=len(self._heap)"),

    # --- the O(running) list rebuild in update_from_output --------------------
    ("vllm/v1/core/sched/utils.py", "def remove_all", "remove_all", "sched_remove_all",
     "n=len(lst), n_remove=len(items_to_remove)"),

    # --- prefix-cache probe and slot allocation for a waiting request ---------
    ("vllm/v1/core/kv_cache_manager.py", "class KVCacheManager", "get_computed_blocks",
     "kv_get_computed_blocks",
     "num_tokens=request.num_tokens, num_blocks=len(request.block_hashes),"
     " num_computed=request.num_computed_tokens"),
    ("vllm/v1/core/kv_cache_manager.py", "class KVCacheManager", "allocate_slots",
     "kv_allocate_slots",
     "num_new_tokens=num_new_tokens, num_computed=request.num_computed_tokens,"
     " num_new_computed=num_new_computed_tokens, num_tokens=request.num_tokens"),

    # --- per-step accounting -------------------------------------------------
    ("vllm/v1/core/sched/scheduler.py", "class Scheduler", "_update_after_schedule",
     "update_after_schedule",
     "num_reqs=len(scheduler_output.num_scheduled_tokens),"
     " num_tokens=scheduler_output.total_num_scheduled_tokens,"
     " num_new=len(scheduler_output.scheduled_new_reqs)"),
    ("vllm/v1/core/sched/scheduler.py", "class Scheduler", "_make_cached_request_data",
     "cached_request_data",
     "num_running=len(running_reqs), num_resumed=len(resumed_reqs),"
     " num_copies=sum(1 for _r in running_reqs"
     " if _r.request_id not in self.prev_step_scheduled_req_ids)"),
    ("vllm/v1/core/sched/scheduler.py", "class Scheduler", "_preempt_request",
     "sched_preempt_request",
     "running=len(self.running), waiting=len(self.waiting),"
     " num_tokens=request.num_tokens"),
]

# ------------------------------------------------- anchored regions in schedule
# (region name, states, first body line (exact, with indentation),
#  end mode): the block runs from the anchor line to the first following
# non-blank line whose indentation is <= `stop_indent`.
ANCHORS = [
    # per-waiting-request evaluation: from just after the peek to the end of
    # the while body.
    ("sched_waiting_eval",
     "num_tokens=request.num_tokens, num_computed=request.num_computed_tokens,"
     " waiting=len(self.waiting)",
     "                    request_id = request.request_id\n", "after", 16),
    # the whole waiting loop
    ("sched_waiting_loop",
     "waiting=len(self.waiting), skipped=len(self.skipped_waiting),"
     " running=len(self.running)",
     "                while (self.waiting or self.skipped_waiting) and token_budget > 0:\n",
     "at", 16),
    # re-queueing the requests skipped this pass
    ("sched_waiting_result",
     "admitted=len(scheduled_new_reqs) + len(scheduled_resumed_reqs),"
     " n_skipped=len(step_skipped_waiting), waiting=len(self.waiting)",
     "                # re-queue requests skipped in this pass ahead of older skipped items.\n",
     "at", 16),
    # the preemption retry inside the running loop
    ("sched_preempt",
     "running=len(self.running), preempted=len(preempted_reqs),"
     " num_new_tokens=num_new_tokens",
     "                        if self.policy == SchedulingPolicy.PRIORITY:\n",
     "at", 24),
]
# for "sched_preempt" the block must stop *after* preempted_reqs.append(...)
STOP_AFTER = {"sched_preempt": "                        preempted_reqs.append(preempted_req)\n",
              "sched_waiting_result": "                    self.prefill_capacity_bound = bool(self.waiting)\n"}


def wrap_method(src, scope, method, region, state):
    """Wrap the body of `method` (indent 4 inside `scope`) in a region."""
    lines = src.splitlines(True)
    scope_re = re.compile(r"%s\b" % re.escape(scope))
    other_re = re.compile(r"(?:class|def)\s+\w")
    module_level = scope.startswith("def ")
    in_scope = False
    i = 0
    indent = 0 if module_level else 4
    while i < len(lines):
        line = lines[i]
        if scope_re.match(line):
            in_scope = True
        elif other_re.match(line):
            in_scope = False
        if in_scope and re.match(r"%sdef %s\(" % (" " * indent, re.escape(method)), line):
            j = i
            depth = 0
            while True:
                depth += lines[j].count("(") - lines[j].count(")")
                if depth <= 0 and lines[j].rstrip().endswith(":"):
                    break
                j += 1
            body_start = j + 1
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
            end = k
            while end < len(lines):
                l = lines[end]
                if l.strip() and (len(l) - len(l.lstrip())) <= indent:
                    break
                end += 1
            if any('perfmark.region("%s"' % region in l for l in lines[k:end]):
                return src, False
            head = "%swith perfmark.region(\"%s\", %s):\n" % (" " * (indent + 4), region, state)
            body = ["    " + l if l.strip() else l for l in lines[k:end]]
            lines[k:end] = [head] + body
            return add_import("".join(lines)), True
        i += 1
    raise SystemExit("vllm_mark_sched.py: %s / %s not found (region %s)" % (scope, method, region))


def add_import(out):
    if "import perfmark\n" not in out:
        m = re.search(r"^(?:from|import) .*\n", out, re.M)
        pos = m.start() if m else 0
        out = out[:pos] + "import perfmark\n" + out[pos:]
    return out


def wrap_block(src, region, state, anchor, mode, stop_indent):
    """Wrap a block of `src` in a region.

    mode "at":    the block starts at the anchor line.
    mode "after": the block starts on the line after the anchor line.
    It ends at the first following non-blank line indented <= stop_indent,
    or just after STOP_AFTER[region] when that is defined.
    """
    lines = src.splitlines(True)
    try:
        a = lines.index(anchor)
    except ValueError:
        raise SystemExit("vllm_mark_sched.py: anchor not found for %s: %r" % (region, anchor))
    start = a if mode == "at" else a + 1
    while mode == "after" and not lines[start].strip():
        start += 1
    if region in STOP_AFTER:
        end = lines.index(STOP_AFTER[region], start) + 1
    else:
        end = start + 1
        while end < len(lines):
            l = lines[end]
            if l.strip() and (len(l) - len(l.lstrip())) <= stop_indent:
                break
            end += 1
    if any('perfmark.region("%s"' % region in l for l in lines[start:end]):
        return src, False
    first = next(l for l in lines[start:end] if l.strip())
    ind = " " * (len(first) - len(first.lstrip()))
    head = "%swith perfmark.region(\"%s\", %s):\n" % (ind, region, state)
    body = ["    " + l if l.strip() else l for l in lines[start:end]]
    lines[start:end] = [head] + body
    return add_import("".join(lines)), True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        raise SystemExit("usage: vllm_mark_sched.py <tree root containing vllm/> [--undo]")
    root = args[0]
    undo = "--undo" in sys.argv
    sched = os.path.join(root, "vllm/v1/core/sched/scheduler.py")
    files = []
    for e in MARKS:
        if e[0] not in files:
            files.append(e[0])
    if "vllm/v1/core/sched/scheduler.py" not in files:
        files.append("vllm/v1/core/sched/scheduler.py")
    if undo:
        for path in files:
            full = os.path.join(root, path)
            if os.path.exists(full + ORIG_SUFFIX):
                shutil.move(full + ORIG_SUFFIX, full)
                print("restored", path)
        return
    for path in files:
        full = os.path.join(root, path)
        if not os.path.exists(full):
            raise SystemExit("no such file: " + full)
        if not os.path.exists(full + ORIG_SUFFIX):
            shutil.copy(full, full + ORIG_SUFFIX)
    # anchored regions first (innermost anchor first), on the untouched text
    src = open(sched).read()
    for region, state, anchor, mode, stop in ANCHORS:
        src, changed = wrap_block(src, region, state, anchor, mode, stop)
        print(("marked block %s" if changed else "already marked block %s") % region)
    open(sched, "w").write(src)
    for path, scope, method, region, state in MARKS:
        full = os.path.join(root, path)
        src = open(full).read()
        out, changed = wrap_method(src, scope, method, region, state)
        if changed:
            open(full, "w").write(out)
            print("marked %s / %s -> %s" % (scope, method, region))
        else:
            print("already marked %s / %s" % (scope, method))


if __name__ == "__main__":
    main()
