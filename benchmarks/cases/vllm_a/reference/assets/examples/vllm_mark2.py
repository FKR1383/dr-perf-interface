"""Add per-step, per-request perfmark regions to the marked COPY of vLLM at
/home/ubuntu/drperf-cases/vllm-cpu-src (on top of the 7 regions that
/home/ubuntu/drperf/examples/vllm_cpu/mark.py inserted), and re-declare the
states of the existing `update_from_output` marker.

    python examples/vllm_mark2.py [ROOT] [--undo]

Measurement only: each method body is wrapped whole in
`with perfmark.region(<name>, <states>):` by mark.py's wrap_method (imported
from the drperf tree, nothing there is modified).  Idempotent.  The state of
each file before this script first touched it is kept as <file>.mark1 (the
pristine originals are mark.py's <file>.orig); --undo restores the .mark1
copies, i.e. goes back to mark.py's 7 regions.
"""
import importlib.util
import os
import re
import shutil
import sys

MARK_PY = "/home/ubuntu/drperf/examples/vllm_cpu/mark.py"
DEFAULT_ROOT = "/home/ubuntu/drperf-cases/vllm-cpu-src"

# file, class, method, region name, declared states (integers available at
# method entry; all form the key)
MARKS = [
    ("vllm/v1/core/sched/scheduler.py", "Scheduler", "_make_cached_request_data", "cached_request_data",
     "num_running=len(running_reqs), num_resumed=len(resumed_reqs)"),
    ("vllm/v1/core/sched/scheduler.py", "Scheduler", "_update_after_schedule", "update_after_schedule",
     "num_reqs=len(scheduler_output.num_scheduled_tokens)"),
    ("vllm/v1/engine/output_processor.py", "OutputProcessor", "process_outputs", "process_outputs",
     "num_outputs=len(engine_core_outputs)"),
    ("vllm/v1/worker/gpu_model_runner.py", "GPUModelRunner", "_update_states", "update_states",
     "num_reqs=len(scheduler_output.num_scheduled_tokens), num_new=len(scheduler_output.scheduled_new_reqs), "
     "num_finished=len(scheduler_output.finished_req_ids)"),
    ("vllm/v1/worker/gpu_model_runner.py", "GPUModelRunner", "_prepare_inputs", "prepare_inputs",
     "num_reqs=len(scheduler_output.num_scheduled_tokens), num_tokens=scheduler_output.total_num_scheduled_tokens"),
]

# Existing markers whose declared states change: file, region, new states.
# update_from_output: self.finished_req_ids is cleared in _update_after_schedule
# (during schedule()) and only refilled by _free_request inside this method, so
# it is empty at entry; keep `running` and add num_reqs (num_tokens was
# collinear with running in decode).
RESTATE = [
    ("vllm/v1/core/sched/scheduler.py", "update_from_output",
     "running=len(self.running), num_reqs=len(scheduler_output.num_scheduled_tokens)"),
]


def load_wrap_method():
    spec = importlib.util.spec_from_file_location("vllm_cpu_mark", MARK_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.wrap_method


def restate(src, region, state):
    pat = re.compile(r'^([ \t]*with perfmark\.region\("%s", )(.*)(\):)$' % re.escape(region), re.M)
    m = pat.search(src)
    if not m:
        raise SystemExit("vllm_mark2.py: marker for region %s not found" % region)
    if m.group(2) == state:
        return src, False
    return src[:m.start(2)] + state + src[m.end(2):], True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else DEFAULT_ROOT
    undo = "--undo" in sys.argv
    files = []
    for entry in MARKS + RESTATE:
        if entry[0] not in files:
            files.append(entry[0])
    if undo:
        for path in files:
            full = os.path.join(root, path)
            keep = full + ".mark1"
            if os.path.exists(keep):
                shutil.move(keep, full)
                print("restored", path)
        return
    wrap_method = load_wrap_method()
    for path in files:
        full = os.path.join(root, path)
        keep = full + ".mark1"
        if not os.path.exists(keep):
            shutil.copy(full, keep)
    for path, cls, method, region, state in MARKS:
        full = os.path.join(root, path)
        src = open(full).read()
        out, changed = wrap_method(src, cls, method, region, state)
        if changed:
            open(full, "w").write(out)
            print("marked %s.%s -> region %s (%s)" % (cls, method, region, state))
        else:
            print("already marked %s.%s" % (cls, method))
    for path, region, state in RESTATE:
        full = os.path.join(root, path)
        src = open(full).read()
        out, changed = restate(src, region, state)
        if changed:
            open(full, "w").write(out)
            print("re-declared region %s (%s)" % (region, state))
        else:
            print("already declared region %s (%s)" % (region, state))


if __name__ == "__main__":
    main()
