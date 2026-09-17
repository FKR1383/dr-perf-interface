### vLLM case E. The output path: a surprise that was mostly the markers

Driver `examples/vllm_run_out.py` runs the same 370-token workload three ways,
FINAL_ONLY through `LLM.generate` and CUMULATIVE and DELTA through the engine
directly. The first measurement, with seven nested Python regions on the
path (`out/vllm_out`), read:

```
process_outputs      cost(num_outputs, num_active) = 82,643.4*num_outputs + 12,842.8*num_active - 20,711.7   52.9% irregular
completion_output    cost(num_tokens, total, kind) = 0*num_tokens + 0*total + 0*kind + 41,722.2               8.3%
request_output       cost(num_outputs, total, prompt, kind) = 0*... + 10,454.7                                8.2%
```

and the reading was that 63% of the per-request per-step cost was
constructing two dataclasses. **That reading was wrong, and the third beat
is what found out.** Reducing the markers to two, with no code change:

```
out/vllm_out        (7 markers)   process_outputs = 82,643.4*num_outputs + 12,842.8*num_active - 20,711.7    52.9%
out/vllm_out_clean  (2 markers)   process_outputs = 30,153.5*num_outputs + 13,663.7*num_active + 2,952.9     26.2%
```

`num_outputs` equals `num_active` at 191 of 194 points, so only their sum is
identified: 95.5k per request per step became 43.8k by removing markers. A
Python region with even one state costs ~11.4k to construct and drperf's
calibration subtracts 582, so five nested regions per request per step were
most of the number. Marker-free and split by output mode
(`out/vllm_out_po_ph_before_*`), the true per-request per-step cost is
8,248 in FINAL_ONLY, 29,780 CUMULATIVE, 30,703 DELTA, and the FINAL_ONLY gap
proves the objects are not built per step: `make_request_output` already
returns early at `output_processor.py:293-296`. What remains is the
detokenizer (`tokenizers::step_decode_stream`, `malloc`, `realloc`,
`memcpy`) and loop bookkeeping. The 12.8k "charge for being alive" was a
collinearity artifact of the same two states; its functions are per-token
detokenization.

**Third beat, measured** (`patches/vllm_output_path.patch`,
`examples/vllm_verify_out.py`, 752 of 752 output records byte-identical):
skipping the `make_request_output` call in FINAL_ONLY rather than entering
it to return saves 1,258 instructions per request per step, 8,247.5 to
6,989.4 (-15.3%), about 80k per step at 64 requests. The lazy string join
for `output_text +=` was implemented, fuzzed over 6,000 schedules with zero
mismatches, and rejected: it saves 0.046 us per step in FINAL_ONLY and costs
0.322 us in CUMULATIVE, which the original formula predicted, since
`1.8*toks - 0.509*have` nets to about zero once `have` is about `4*toks`.

**What this case is for.** It is the cautionary one: a nested-marker layout
produced a plausible, attributable, wrong surprise, and only the discipline
of re-measuring with fewer markers before optimising caught it. The two
signs were there in the first output, a negative constant and a 53% irregular
share on a region whose work should be regular, and the caveat about marker
construction cost was already written in this document's notes without
being applied to these numbers.

---

