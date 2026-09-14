"""Insert perfmark regions into the SAMPLING path of a vLLM source tree.

    python examples/mark_samp.py /home/ubuntu/drperf-cases/vllm-cpu-samp/vllm [--undo]

Same mechanics as /home/ubuntu/drperf/examples/vllm_cpu/mark.py (whole method
body wrapped in `with perfmark.region(...)`), extended to module-level
functions.  Annotation only: no behaviour change, no reordering.  Idempotent.
"""
import os
import re
import shutil
import sys

# (file, class-or-None, function, region, declared integer states)
MARKS = [
    # --- penalties: the padded tensor over ALL requests' output histories ---
    ("vllm/v1/sample/ops/penalties.py", None, "apply_all_penalties", "apply_penalties",
     "num_reqs=len(output_token_ids), "
     "max_len=max((len(o) for o in output_token_ids), default=0), "
     "total_tokens=sum(len(o) for o in output_token_ids)"),
    ("vllm/v1/sample/ops/penalties.py", None, "_convert_to_tensors", "pen_tensors",
     "num_reqs=len(output_token_ids), "
     "max_len=max((len(o) for o in output_token_ids), default=0), "
     "total_tokens=sum(len(o) for o in output_token_ids)"),
    # --- top-k / top-p sampler forward (the CPU-bound one) ---
    ("vllm/v1/sample/ops/topk_topp_sampler.py", "TopKTopPSampler", "forward_cpu", "topk_topp",
     "num_reqs=logits.shape[0], k=(int(k.max()) if k is not None else 0), "
     "p_flag=(1 if p is not None else 0)"),
    # --- the non-argmax-invariant logits-processor chain + penalties ---
    ("vllm/v1/sample/sampler.py", "Sampler", "apply_logits_processors", "logitsprocs",
     "num_reqs=logits.shape[0]"),
    # --- per-step rebuild of the sampling metadata ---
    ("vllm/v1/worker/gpu_input_batch.py", "InputBatch", "refresh_metadata", "refresh_metadata",
     "num_reqs=self.num_reqs, num_new=len(self.batch_update_builder.added), "
     "num_removed=len(self.batch_update_builder._removed), "
     "num_moved=len(self.batch_update_builder.moved)"),
    ("vllm/v1/worker/gpu_input_batch.py", "InputBatch", "_make_sampling_metadata", "make_sampling_metadata",
     "num_reqs=self.num_reqs, "
     "max_prompt=(int(self.num_prompt_tokens[:self.num_reqs].max()) if self.num_reqs else 0)"),
]


def wrap(src, cls, func, region, state):
    lines = src.splitlines(True)
    ind = 4 if cls else 0
    in_class = cls is None
    i = 0
    while i < len(lines):
        line = lines[i]
        if cls is not None:
            if re.match(r"class %s\b" % re.escape(cls), line):
                in_class = True
            elif re.match(r"class \w", line):
                in_class = False
        if in_class and re.match(r"%sdef %s\(" % (" " * ind, re.escape(func)), line):
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
                if l.strip() and (len(l) - len(l.lstrip())) <= ind:
                    break
                end += 1
            if any('perfmark.region("%s"' % region in l for l in lines[k:end]):
                return src, False
            head = '%swith perfmark.region("%s", %s):\n' % (" " * (ind + 4), region, state)
            body = ["    " + l if l.strip() else l for l in lines[k:end]]
            lines[k:end] = [head] + body
            out = "".join(lines)
            if "import perfmark\n" not in out:
                m = re.search(r"^(?:from|import) .*\n", out, re.M)
                pos = m.start() if m else 0
                out = out[:pos] + "import perfmark\n" + out[pos:]
            return out, True
        i += 1
    raise SystemExit("mark_samp.py: %s.%s not found" % (cls, func))


def main():
    root = sys.argv[1]
    undo = "--undo" in sys.argv
    for path, cls, func, region, state in MARKS:
        full = os.path.join(root, path)
        orig = full + ".sampmark.orig"
        if undo:
            if os.path.exists(orig):
                shutil.move(orig, full)
                print("restored", path)
            continue
        if not os.path.exists(orig):
            shutil.copy(full, orig)
        src = open(full).read()
        out, changed = wrap(src, cls, func, region, state)
        if changed:
            open(full, "w").write(out)
            print("marked %s.%s -> region %s" % (cls, func, region))
        else:
            print("already marked %s.%s" % (cls, func))


if __name__ == "__main__":
    main()
