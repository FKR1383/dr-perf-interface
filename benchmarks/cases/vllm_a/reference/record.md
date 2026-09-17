### vLLM case A. The scheduler side per step: a fixed tax, a step function, and a rebuild

Late attach makes vLLM measurable at will: a stateless region placed after
`LLM(...)` returns, run with `--late`, cuts the identical workload from 300.6 s
to 24.7 s (native 11.2 s), and the seven baseline formulas reproduce to within
noise (`out/vllm_late`). Five regions were then added around the per-step,
per-request paths between `schedule` and `execute_model`
(`examples/vllm_mark2.py`), and the run widened to ten requests
(`out/vllm_marked`, 27.3 s).

```
prepare_inputs        cost(num_reqs, num_tokens) = 758.2*num_reqs + 106.9*num_tokens + 464,927.7                    20.9% irregular
update_states         cost(num_reqs, num_new, num_finished) = 1,825.7*num_reqs + 27,753.1*num_new + 11,182.4*num_finished + 58,977.5   55.1%
update_from_output    cost(running, num_reqs) = 7,276.4*running + 0*num_reqs + 34,806.7                              57.7%
cached_request_data   cost(num_running, num_resumed) = 4,907.1*num_running + 0*num_resumed + 13,107.9                  3.8%
update_after_schedule cost(num_reqs) = 2,924.4*num_reqs + 5,041.7                                                     3.9%
process_outputs       cost(num_outputs) = 2,225.9*num_outputs + 65,341.3   [num_outputs >= 6]                        52-56%
```

**The fixed tax.** `GPUModelRunner._prepare_inputs` costs about 580k
instructions per step whether the batch holds one request or ten (trace
range 560k-633k), against 758 per request. The constant is attributed to
torch dispatch, `__tls_get_addr` 13.2k, `pthread_mutex_lock/unlock` 17.5k,
`_PyArg_ParseStack` 9.1k, `OperatorEntry::lookup` 6.2k: about 35 tiny tensor
ops per step (`copy_to_gpu` at `v1/utils.py:139`, which is a real `copy_` on
this backend, block-table commit at `gpu_model_runner.py:2037`, slices of
positions and sequence lengths, `compute_slot_mapping` at 2255,
`_prepare_input_ids` at 2262). At 64 requests the per-request work is ~55k
and the fixed part ~580k, ten to one. The formula says the batch size is not
what to optimise here; the op count is.

**Third beat for the fixed tax, measured** (`patches/vllm_prepare_inputs.patch`,
`out/vllm_marked_fix`). Temporary nested markers first split the constant
into its sub-steps on a steady ten-request step, then were removed:

```
sub-step                                        before     after
positions/seq_lens to "device"                 105,654    11,101
numpy index prep (repeat, cumsum, gather idx)   85,398    85,419
prev_positions + num_tokens list + mask         79,937    48,093
req_indices/query_pos/num_scheduled H2D         76,610     8,451
compute_slot_mapping                            54,433    53,899
optimistic seq_lens (add + fill_)               44,953    11,647
tail (logits_indices, np.ones)                  36,254    23,158
num_computed_tokens copy                        24,193     5,731
index_select gather                             23,386    23,677
block-table commit                              23,125     4,078
_prepare_input_ids                              22,527     3,474
query_start_loc                                 18,863    15,707
num_accepted_tokens                             10,579     3,740
total                                          665,834   357,660
```

The finding under the finding: `CPUModelRunner._postprocess_tensors` sets
`buffer.gpu = buffer.cpu`, so on this backend every `copy_to_gpu` copies a
tensor onto itself, about 6k instructions of dispatch each, and several
device ops recompute values numpy had already produced. The change makes
`copy_to_gpu` return when the two alias, keeps numpy views of the per-step
buffers, and fills `positions`/`seq_lens`/`logits_indices` from the numpy
values already in hand, guarded so the original device path runs when they
are not aliased. All ten requests' token ids, text, cumulative logprob and
finish reason are byte-identical.

```
prepare_inputs   before  758.2*num_reqs + 106.9*num_tokens + 464,927.7     20.9% irregular
                 after   721.3*num_reqs +  55.2*num_tokens + 205,310.3     26.0%
execute_model    constant 9,224,201 -> 8,968,063; both slopes unchanged to six figures
```

The constant fell 56% and `execute_model`'s constant fell by the same 256k,
which is the composition identity doing its job. At 64 decode requests:
520k to 255k per step. What remains is real work, the numpy index build
(85k over nine calls), the slot-mapping kernel (54k), the gather (23k), and a
20k list comprehension over a Python property that would need an int32
mirror in `_update_states` to remove.

**The step function.** `_update_states` on a steady ten-request step costs
85k; any step in which a request finished costs 205k-265k, and the extra does
not depend on whether one or two finished; each new request adds 70k-90k.
The 55% unexplained share is exactly that: a per-event cost that `derive`
cannot put into a per-count coefficient. The event is `condense()`
(`gpu_input_batch.py:708`) followed by `refresh_metadata()` rebuilding the
sampling metadata with several `copy_slice` ops (840-860, called from
`gpu_model_runner.py:1567`), and per arrival the elementwise assignment
`token_ids_cpu[req_index, :n] = request.prompt_token_ids` (376), 4.5k
instructions of list-to-int32 conversion per prompt. Under continuous
admission at 64 concurrent requests nearly every step pays the ~150k.

**The rebuild.** `_make_cached_request_data` costs 4.9k per running request
per step at 3.8% unexplained, so it is exactly what it looks like:
`get_block_ids` (`kv_cache_manager.py:77-92`) constructs a fresh tuple of
lists and two generator functions per request per step (`PyFunction_New` 242
per request) and the whole `CachedRequestData` (scheduler.py:1525) is rebuilt
from scratch, then walked again in `_update_states`. At 64 requests about
0.33M instructions per step for state that, in steady decode, changed by one
integer per request.

**Third beat for the rebuild, measured** (`patches/vllm_cached_request_data.patch`,
copy `vllm-cpu-rb`, `out/vllm_rb_base` -> `out/vllm_rb_fix`; text, token ids,
cumulative logprob and finish reasons identical for all ten requests):

```
cached_request_data   4,916.2*num_running + 13,027.5    4.2%   ->   1,671*num_running + 15,247.4    3.7%
update_states (consumer)  1,826.5*num_reqs + 27,735*num_new + 11,104*num_finished + 58,905   ->   1,830.8*num_reqs + 27,845*num_new + 11,185*num_finished + 59,088   (unchanged)
```

Fifteen decode steps in sixteen a request gets no new blocks, and the
manager already returns a singleton empty object for that case, so the
scheduler now appends `None` without calling `get_block_ids` at all; the
single-group fast path drops the two generator functions; the five bound
methods and the flags are hoisted out of the loop; and the token list is
stored as the tail the one consumer reads (`gpu_model_runner.py:1527`)
instead of a copy of the whole prompt. Per request the interpreter cost
falls from 2,826 to 1,297. At 64 running requests: 328k to 122k per step.

**Relations** (`out/vllm_marked/learn.txt`, exact at every trigger):

```
cached_request_data.num_running = last(schedule.running)
update_states.num_new      = last(execute_model.num_reqs) - last(schedule.running)
update_states.num_finished = last(prepare_inputs.num_reqs) - last(schedule.running)
schedule.waiting           = cum(generate_loop.unfinished) - cum(update_states.num_new)
```

The last two are worth pausing on: the number of finished requests the model
runner will process is learned as "what the runner prepared last step minus
what the scheduler still has running", and the waiting queue as "everything
submitted minus everything the runner has admitted", both without reading a
line of the scheduler.

---

