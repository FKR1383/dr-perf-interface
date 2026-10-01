# agent_PCVs: full-feedback PCV selector

You are the only PCV-selection agent for exactly one benchmark case. Your
conversation persists across that case's iterations and is never reused for
another case. You have no tools and cannot execute Dr. Perf directly. Treat
Dr. Perf as a black box: you propose a candidate, a trusted deterministic
script validates it and runs Dr. Perf, and on the next turn you receive the
complete Dr. Perf metrics report produced for that candidate.

Select between 1 and 4 cheap state expressions available when the marked
region is entered that explain its instruction count. Any cheap mathematical
derivation of entry state is allowed, including products, powers, comparisons,
conditional expressions, and cardinalities; runtime/library entry state is
also allowed. Avoid side effects, expensive computation, filesystem access,
counters, timers, and values outside signed 64-bit range.

The workload, target implementation, marker boundary, and correctness checks
are fixed for the entire case. Never propose changes to them. Return only the
candidate JSON required by the schema. Success requires valid irregularity
strictly below 10 percent. Coefficients are fitted by Dr. Perf; do not provide
coefficients as separate output.

This is iteration 4. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Batch size, completions, and first-output prompt length explain ordinary work. A separate regime for batches that finish entirely on their first output may isolate the largest residual; this remains a hypothesis rather than an established cause.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "len(engine_core_outputs)",
        "name": "batch_size",
        "rationale": "Captures per-request processing and output construction."
      },
      {
        "expression": "sum((o.finish_reason is not None for o in engine_core_outputs))",
        "name": "finished_requests",
        "rationale": "Captures completion statistics and cleanup."
      },
      {
        "expression": "sum((self.request_states[o.request_id].prompt_len for o in engine_core_outputs if o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling))",
        "name": "prefill_prompt_tokens",
        "rationale": "Captures prompt-dependent first-output detokenization work."
      },
      {
        "expression": "int(len(engine_core_outputs) > 0 and sum((o.finish_reason is not None and o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling for o in engine_core_outputs)) == len(engine_core_outputs))",
        "name": "entire_batch_finishes_on_first_output",
        "rationale": "Separates batches completed entirely on their first output, including the exceptional high-cost observation."
      }
    ]
  },
  "case_id": "vllm-047",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-047",
    "distinct_states": 18,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "batch_size": 11115.323663163615,
        "entire_batch_finishes_on_first_output": 131901.94097705575,
        "finished_requests": 25173.07563847355,
        "prefill_prompt_tokens": 1487.3999516223698
      },
      "constant": 18466.862623257803,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 130.44300819560885,
    "max_unexplained_share": 0.3929481326492725,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "finished_requests",
      "prefill_prompt_tokens",
      "entire_batch_finishes_on_first_output"
    ],
    "raw_files": [
      "run.2328237.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 50055.4,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 5435.599999999999,
        "unexplained_share": 0.10859168041809673
      },
      {
        "calls": 1,
        "instructions_per_call": 239732.0,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 1,
          "finished_requests": 1,
          "prefill_prompt_tokens": 10
        },
        "unexplained_instructions_per_call": 44516.0,
        "unexplained_share": 0.1856906879348606
      },
      {
        "calls": 1,
        "instructions_per_call": 35864.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 4331.0,
        "unexplained_share": 0.12076176667410217
      },
      {
        "calls": 1,
        "instructions_per_call": 114009.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_prompt_tokens": 20
        },
        "unexplained_instructions_per_call": 43557.0,
        "unexplained_share": 0.38204878562218775
      },
      {
        "calls": 4,
        "instructions_per_call": 72816.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 12496.75,
        "unexplained_share": 0.1716209349593496
      },
      {
        "calls": 2,
        "instructions_per_call": 95543.5,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 9788.0,
        "unexplained_share": 0.10244548294755793
      },
      {
        "calls": 2,
        "instructions_per_call": 80589.5,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 8735.5,
        "unexplained_share": 0.10839501423882764
      },
      {
        "calls": 1,
        "instructions_per_call": 269434.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 66
        },
        "unexplained_instructions_per_call": 94636.0,
        "unexplained_share": 0.3512400068291307
      },
      {
        "calls": 1,
        "instructions_per_call": 111134.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 10986.0,
        "unexplained_share": 0.0988536361509529
      },
      {
        "calls": 1,
        "instructions_per_call": 342000.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 84
        },
        "unexplained_instructions_per_call": 123032.0,
        "unexplained_share": 0.35974269005847953
      },
      {
        "calls": 2,
        "instructions_per_call": 125519.5,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 12863.5,
        "unexplained_share": 0.10248208445699672
      },
      {
        "calls": 1,
        "instructions_per_call": 108759.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 12104.0,
        "unexplained_share": 0.11129193905791705
      },
      {
        "calls": 1,
        "instructions_per_call": 140234.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 14308.0,
        "unexplained_share": 0.10202946503700958
      },
      {
        "calls": 1,
        "instructions_per_call": 753902.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 230
        },
        "unexplained_instructions_per_call": 283863.0,
        "unexplained_share": 0.3765250655920796
      },
      {
        "calls": 1,
        "instructions_per_call": 856454.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_tokens": 270
        },
        "unexplained_instructions_per_call": 336542.0,
        "unexplained_share": 0.3929481326492725
      },
      {
        "calls": 1,
        "instructions_per_call": 155013.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0
        },
        "unexplained_instructions_per_call": 16039.0,
        "unexplained_share": 0.10346874133137221
      },
      {
        "calls": 1,
        "instructions_per_call": 1028690.0,
        "state": {
          "batch_size": 7,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 322
        },
        "unexplained_instructions_per_call": 394841.0,
        "unexplained_share": 0.3838289474963303
      },
      {
        "calls": 1,
        "instructions_per_call": 1178468.0,
        "state": {
          "batch_size": 8,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_tokens": 368
        },
        "unexplained_instructions_per_call": 456988.0,
        "unexplained_share": 0.38778142469714916
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 39.29481326492725,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 39.29481326492725,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17"
  }
}