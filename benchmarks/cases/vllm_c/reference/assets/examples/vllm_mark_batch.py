"""Add perfmark regions for the CPU-side model runner / persistent batch to the
copy of vLLM at /home/ubuntu/drperf-cases/vllm-cpu-batch (on top of the 7
regions that /home/ubuntu/drperf/examples/vllm_cpu/mark.py already inserted).

    python examples/vllm_mark_batch.py [ROOT] [--undo]

Measurement only: each method body is wrapped whole in
`with perfmark.region(<name>, <states>):` by mark.py's wrap_method (imported
from the drperf tree; nothing there is modified).  Idempotent.  The state of
each file before this script first touched it is kept as <file>.markb.
"""
import importlib.util
import os
import shutil
import sys

MARK_PY = "/home/ubuntu/drperf/examples/vllm_cpu/mark.py"
DEFAULT_ROOT = "/home/ubuntu/drperf-cases/vllm-cpu-batch"

# file, class, method, region name, declared states (integers available at
# method entry; all of them form the key)
MARKS = [
    ("vllm/v1/worker/gpu_model_runner.py", "GPUModelRunner", "_update_states", "update_states",
     "num_reqs=len(scheduler_output.num_scheduled_tokens), "
     "num_new=len(scheduler_output.scheduled_new_reqs), "
     "num_finished=len(scheduler_output.finished_req_ids)"),
    ("vllm/v1/worker/gpu_model_runner.py", "GPUModelRunner", "_prepare_inputs", "prepare_inputs",
     "num_reqs=len(scheduler_output.num_scheduled_tokens), "
     "num_tokens=scheduler_output.total_num_scheduled_tokens"),
    ("vllm/v1/worker/gpu_input_batch.py", "InputBatch", "add_request", "add_request",
     "num_prompt=(len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0), "
     "num_blocks=sum(len(b) for b in request.block_ids)"),
    ("vllm/v1/worker/gpu_input_batch.py", "InputBatch", "remove_request", "remove_request",
     "num_reqs=self.num_reqs"),
    ("vllm/v1/worker/gpu_input_batch.py", "InputBatch", "condense", "condense",
     "num_reqs=self.num_reqs, empty=len(self.batch_update_builder._removed)"),
    ("vllm/v1/worker/gpu_input_batch.py", "InputBatch", "refresh_metadata", "refresh_metadata",
     "num_reqs=self.num_reqs, num_added=len(self.batch_update_builder.added), "
     "num_moved=len(self.batch_update_builder.moved)"),
    ("vllm/v1/worker/block_table.py", "MultiGroupBlockTable", "append_row", "bt_append_row",
     "num_blocks=sum(len(b) for b in block_ids)"),
    ("vllm/v1/worker/block_table.py", "MultiGroupBlockTable", "commit_block_table", "bt_commit",
     "num_reqs=num_reqs"),
]


def load_wrap_method():
    spec = importlib.util.spec_from_file_location("vllm_cpu_mark", MARK_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.wrap_method


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else DEFAULT_ROOT
    undo = "--undo" in sys.argv
    files = []
    for entry in MARKS:
        if entry[0] not in files:
            files.append(entry[0])
    if undo:
        for path in files:
            full = os.path.join(root, path)
            keep = full + ".markb"
            if os.path.exists(keep):
                shutil.move(keep, full)
                print("restored", path)
        return
    wrap_method = load_wrap_method()
    for path in files:
        full = os.path.join(root, path)
        keep = full + ".markb"
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


if __name__ == "__main__":
    main()
