### vLLM case F. Prefix caching: what a block hash costs, and a conservation law for resident KV

Driver `examples/vllm_run2_kv.py`: a ~50-token shared prefix, prompts of 60
to 600 tokens, `block_size` 16 so blocks fill during decode, twelve then
twenty-four requests (`out/vllm_kv`, `out/vllm_kv24`; 36 s and 41 s with late
attach). Seven markers from `examples/vllm_mark_kv.py`.

```
kv_cache_full_blocks    cost(num_new, num_cached) = 7,267.2*num_new + 0*num_cached + 4,521.4                          7.1% irregular
    per new block: _PyEval_EvalFrameDefault 3,992, _Py_HashBytes 198, PyBytes_FromString 160, PyLong_AsUnsignedLong 153
kv_get_computed_blocks  cost(num_tokens, num_hashes) = 768.6*num_tokens - 6,161.1*num_hashes + 13,486.4                2.3%
kv_block_hasher         cost(num_hashes, num_tokens) = -16,664*num_hashes + 1,041.1*num_tokens - 6,764.7               15.0%   (degenerate: num_hashes = num_tokens // 16)
kv_allocate_slots       cost(num_new_tokens, num_computed) = 245.4*num_new_tokens + 0.105*num_computed + 15,372.6     66.7%
kv_free                 cost(num_blocks, num_tokens) = 424.2*num_blocks - 12*num_tokens + 7,497.4   (24 requests)     48.1%
kv_common_prefix_blocks cost(num_running, num_blocks) = 0*num_running + 0*num_blocks + 1,750.7                       70.2%
detokenize_update       cost(num_new, text_len) = 0*num_new + 0*text_len + 5,349.1                                   72.5%
```

**A block hash is three copies and two hashes.** Per 16-token block the
hasher costs about 19,700 instructions (730,164 for a 37-block prompt in
the trace). `kv_cache_utils.py:717` slices `request.all_token_ids[i:j]`,
which `ConstantList.__getitem__` (`v1/utils.py:80`) returns as a fresh list;
`:601` copies it into a tuple; `hashing.py:39` pickles it and runs SHA-256.
Then the 32-byte digest is re-hashed by CPython on every probe and insert:
`make_block_hash_with_group_id` (`:67`) allocates a 36-byte key each time,
and `_insert_block_hash` hashes it twice, `contain()` at `block_pool.py:616`
and `insert()` at `:627`. The signature is in the per-new-block column:
`_Py_HashBytes`, `PyBytes_FromString`, `PyLong_AsUnsignedLong`. A 2k-token
prompt is 125 blocks, ~2.5M instructions to hash on admission; probing the
prefix cache costs ~6,900 per block for what is one dictionary lookup.

**The no-op calls cost more than the work.** `request_block_hasher` runs on
every generated token (`Request.append_output_token_ids`); fifteen calls in
sixteen return at `:695` having hashed nothing, at 1,677-1,990 instructions
each. Amortised, the wasted entry cost (~1,594 per token) exceeds the real
hashing (~1,294 per token). `kv_allocate_slots` has the same shape at a
larger scale, ~36,500 instructions per request per step to allocate one
token's worth of slot. Per concurrent request per decode step, hasher plus
allocate plus detokenize come to ~50k of Python before any model work.

**A per-step scan of the shared prefix.** `get_num_common_prefix_blocks`
(`single_type_kv_cache_manager.py:823-830`) runs every step on `running[0]`
and walks its blocks while `ref_cnt == len(self.req_to_blocks)`, evaluating
`len()` inside the loop. Both declared states got coefficient 0 and the
region reads 70% unexplained, because the cost follows neither: the trace
gives ~580 per block scanned, 22,939 at 40 blocks against 3,233 at six. It
scales with the shared prefix in blocks, not with the batch: a 500-token
system prompt is ~21k per scheduler step, at any batch size.

**Third beat for the prefix scan, measured** (`patches/vllm_common_prefix.patch`,
`out/vllm_rb_kvbase` -> `out/vllm_rb_kvfix`; the value returned at every
scheduler step logged and identical, outputs identical):

```
kv_common_prefix_blocks   0*num_running + 0*num_blocks + 1,765.4    70.0%   ->   0*num_running + 0*num_blocks + 2,934.3    8.8%
per call, own thread: 40 blocks 22,800 -> 6,767; 29 blocks 15,121 -> 5,167; 21 blocks 11,360 -> 4,393; 4 blocks 3,279 -> 2,778
```

`len()` is hoisted out of the loop and the result memoised on (request id,
number of running requests, block count, a ref-count epoch bumped at every
mutation that can touch a held block: `touch`, `free_blocks`, the two
copy-on-write sites; `get_new_blocks` only appends, which the block count
already keys). Hit rate 65% on this workload, blocks scanned 400 to 142.
At a 500-token shared prefix about 21k to 3k per step on a hit, at any batch
size. The constant rose because the scan stopped hiding in the residue.

**Relations** (`out/vllm_kv/learn.txt`, `out/vllm_kv24/learn.txt`):

```
attention.kv_tokens = count(detokenize_update) - cum(kv_free.num_tokens) + cum(kv_get_computed_blocks.num_tokens)   (504/504)
kv_free.num_blocks  = last(kv_common_prefix_blocks.num_blocks)                                                       (25/25)
schedule.running    = count(kv_get_computed_blocks) - count(kv_free)
engine_step.unfinished = cum(generate_loop.unfinished) - count(kv_free)
```

The first is the KV cache's conservation law, recovered from counts alone:
what attention has to read is every prompt token admitted, plus one per
detokenised output, minus every token freed. It held at all 504 attention
calls.

**Third beat, measured** (`patches/vllm_kv_hash.patch`, `out/vllm_kv_fix`,
24 requests, identical text, identical 456 block hashes in production
order, identical prefix-cache hits):

```
                                   before                       after
hasher per 16-token block          19,630 + 1,746 per call      19,009 + 2,182   (-3.2%)
no-op per-token hasher calls       530 of 592 triggers          0 of 62; the call is gone
no-op call, native micro           2,327                        1,334            (-993 per call)
kv_cache_full_blocks               7,266*num_new + 4,480        6,839.6*num_new + 4,765.2   (-5.9% per block)
```

Three changes: the hasher's boundary test moved to the caller so the
fifteen no-op calls per block never happen; the `ConstantList` frame per
slice hoisted out of the loop; and `contain()` + `insert()` replaced by one
`setdefault`. The equivalence check needed `PYTHONHASHSEED` pinned, because
`NONE_HASH` is `os.urandom(32)` otherwise. Per decode step at 64 requests the
saving is about 64k instructions; per 2k-token prompt about 134k, 3.9% of the
~3.4M spent hashing and inserting it.

**And a correction the third beat forced.** The "three copies" reading
above was wrong in proportion. A per-step micro-measurement of one block
gives: `ConstantList` slice 1,986 (of which the Python frame 688), the tuple
649, `pickle.dumps` 6,263, `sha256` 4,207, `generate_block_hash_extra_keys`
4,825. The copies are a tenth of the block; the serialisation is the cost,
and it is load-bearing: the tuple is what gets pickled, a list pickles to
different bytes, and the one-copy route through `islice` costs 1.8x more.
What the surprise reduces to is that the hash input is built by the
general-purpose pickler, ~6k for sixteen integers.

**A lesson on declared states.** `num_hashes` is `num_tokens // 16` at every
point, so the two hashing regions fitted a degenerate plane with a negative
`num_hashes` coefficient and a negative constant. A derived state carries
no information the base state lacks and costs a degree of freedom; the
useful second state would have been the one the code branches on, whether
this call crossed a block boundary.

---

