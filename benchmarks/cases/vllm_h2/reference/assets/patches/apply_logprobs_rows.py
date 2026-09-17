"""Restrict the sampler's vocabulary-wide top-k to the rows that asked for
sample logprobs.

    python patches/apply_logprobs_rows.py <tree containing vllm/> [--undo]

`InputBatch.max_num_logprobs` is a batch-wide maximum, so `Sampler.forward`
runs `torch.topk` over the whole [num_reqs, vocab] logprob matrix as soon as a
single request sets `logprobs=k`.  The rows belonging to requests that did not
ask are never read: `Scheduler.update_from_output` slices `logprobs` per
request only when `sampling_params.num_logprobs is not None`.

Measured on the CPU backend (drperf, out/vllm_stop): `gather_logprobs` costs
1,009,495 instructions per row in the batch, 913,749 of them in
`at::native::AVX2::topk_impl_loop`, independent of how many rows asked.

Indentation-agnostic so it applies both to a pristine tree and to the
perfmark-annotated copy.  Idempotent; --undo restores the .lp.orig backups.
"""
import os
import re
import shutil
import sys

FILES = [
    "vllm/v1/sample/metadata.py",
    "vllm/v1/worker/gpu_input_batch.py",
    "vllm/v1/sample/sampler.py",
]

META_ANCHOR = (
    "    thinking_budget_state_holder: ThinkingBudgetStateHolder | None = None\n")
META_ADD = """
    # Row indices (into the sampled dimension) of the requests that asked for
    # sample logprobs, paired with the number of rows the mapping was built
    # for.  None means every row wants them, or the mapping is unavailable.
    logprobs_rows: tuple[int, torch.Tensor] | None = None
"""

BATCH_ANCHOR = "        return SamplingMetadata(\n"
BATCH_ADD = """        # Row indices of the requests that asked for sample logprobs.  When
        # only part of the batch asked, `Sampler` keeps the vocabulary-wide
        # top-k off the rows nothing will read.
        logprobs_rows: tuple[int, torch.Tensor] | None = None
        if self.num_logprobs and len(self.num_logprobs) < num_reqs:
            rows = sorted(
                self.req_id_to_index[req_id]
                for req_id in self.num_logprobs
                if req_id in self.req_id_to_index
            )
            if rows and len(rows) < num_reqs:
                logprobs_rows = (
                    num_reqs,
                    torch.tensor(rows, dtype=torch.int64, device=self.device),
                )

"""
BATCH_FIELD_ANCHOR = "            max_num_logprobs=self.max_num_logprobs,\n"
BATCH_FIELD_ADD = "            logprobs_rows=logprobs_rows,\n"

SAMPLER_OLD = re.compile(
    r"( *)else:\n"
    r" *# Gather the logprobs and ranks of the topk and sampled token\.\n"
    r" *logprobs_tensors = self\.gather_logprobs\(\n"
    r" *raw_logprobs, num_logprobs, token_ids=sampled\n"
    r" *\)\n")

SAMPLER_NEW = """{i}else:
{i}    # Gather the logprobs and ranks of the topk and sampled token.
{i}    # `max_num_logprobs` is a batch-wide maximum, so without the
{i}    # restriction below every row pays the vocabulary-wide top-k as
{i}    # soon as one request asks for logprobs.
{i}    rows = sampling_metadata.logprobs_rows
{i}    if rows is not None and rows[0] == raw_logprobs.shape[0]:
{i}        logprobs_tensors = self._gather_logprobs_rows(
{i}            raw_logprobs, num_logprobs, sampled, rows[1]
{i}        )
{i}    else:
{i}        logprobs_tensors = self.gather_logprobs(
{i}            raw_logprobs, num_logprobs, token_ids=sampled
{i}        )
"""

METHOD_ANCHOR = "    @staticmethod\n    def gather_logprobs(\n"
METHOD_ADD = '''    def _gather_logprobs_rows(
        self,
        logprobs: torch.Tensor,
        num_logprobs: int,
        token_ids: torch.Tensor,
        rows: torch.Tensor,
    ) -> LogprobsTensors:
        """`gather_logprobs` for `rows` only, padded back to full height.

        The rows no request asked about are left at zero; nothing reads them
        (`Scheduler.update_from_output` slices per request and only for a
        request whose `sampling_params.num_logprobs` is set).
        """
        sub = self.gather_logprobs(
            logprobs[rows], num_logprobs, token_ids=token_ids[rows]
        )
        n = logprobs.shape[0]
        width = sub.logprob_token_ids.shape[1]
        ids = logprobs.new_zeros((n, width), dtype=sub.logprob_token_ids.dtype)
        lps = logprobs.new_zeros((n, width), dtype=sub.logprobs.dtype)
        ranks = logprobs.new_zeros((n,), dtype=sub.selected_token_ranks.dtype)
        ids.index_copy_(0, rows, sub.logprob_token_ids)
        lps.index_copy_(0, rows, sub.logprobs)
        ranks.index_copy_(0, rows, sub.selected_token_ranks)
        return LogprobsTensors(ids, lps, ranks)

'''


def edit(path, fn):
    src = open(path).read()
    out = fn(src)
    if out is None:
        print("already patched", path)
        return
    open(path, "w").write(out)
    print("patched", path)


def do_meta(src):
    if "logprobs_rows" in src:
        return None
    assert META_ANCHOR in src, "metadata.py anchor"
    return src.replace(META_ANCHOR, META_ANCHOR + META_ADD, 1)


def do_batch(src):
    if "logprobs_rows" in src:
        return None
    assert BATCH_ANCHOR in src, "gpu_input_batch.py anchor"
    src = src.replace(BATCH_ANCHOR, BATCH_ADD + BATCH_ANCHOR, 1)
    assert BATCH_FIELD_ANCHOR in src, "gpu_input_batch.py field anchor"
    return src.replace(BATCH_FIELD_ANCHOR,
                       BATCH_FIELD_ANCHOR + BATCH_FIELD_ADD, 1)


def do_sampler(src):
    if "_gather_logprobs_rows" in src:
        return None
    m = SAMPLER_OLD.search(src)
    assert m, "sampler.py gather branch anchor"
    src = src[:m.start()] + SAMPLER_NEW.format(i=m.group(1)) + src[m.end():]
    assert METHOD_ANCHOR in src, "sampler.py method anchor"
    return src.replace(METHOD_ANCHOR, METHOD_ADD + METHOD_ANCHOR, 1)


def main():
    root = sys.argv[1]
    undo = "--undo" in sys.argv
    for rel, fn in zip(FILES, (do_meta, do_batch, do_sampler)):
        full = os.path.join(root, rel)
        keep = full + ".lp.orig"
        if undo:
            if os.path.exists(keep):
                shutil.move(keep, full)
                print("restored", rel)
            continue
        if not os.path.exists(keep):
            shutil.copy(full, keep)
        edit(full, fn)


if __name__ == "__main__":
    main()
