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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Initial text conversion may scale with non-special prompt tokens. Removing the optional leading special token tests a structural source of mismatch in the raw prompt-length feature.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "len(engine_core_outputs)",
        "name": "batch_size",
        "rationale": "Captures per-request processing and output construction."
      },
      {
        "expression": "sum((o.finish_reason is not None for o in engine_core_outputs))",
        "name": "finished_requests",
        "rationale": "Restores an independent count of completion-statistics and cleanup operations."
      },
      {
        "expression": "sum((self.request_states[o.request_id].prompt_len - int(bool(self.request_states[o.request_id].prompt_token_ids) and self.request_states[o.request_id].prompt_token_ids[0] == 2) for o in engine_core_outputs if o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling))",
        "name": "prefill_text_tokens",
        "rationale": "Counts initial prompt tokens excluding OPT's leading special token, accounting for the workload's alternating add_special_tokens setting."
      },
      {
        "expression": "int(len(engine_core_outputs) > 0 and sum((o.finish_reason is not None and o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling for o in engine_core_outputs)) == len(engine_core_outputs))",
        "name": "entire_batch_finishes_on_first_output",
        "rationale": "Restores independent separation of the exceptional first-output completion regime."
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
        "batch_size": 10631.30527550328,
        "entire_batch_finishes_on_first_output": 131487.38185487196,
        "finished_requests": 25173.357438270745,
        "prefill_text_tokens": 1339.3313657556982
      },
      "constant": 19000.50035464925,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 139.4639059593901,
    "max_unexplained_share": 0.44057427397462917,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "finished_requests",
      "prefill_text_tokens",
      "entire_batch_finishes_on_first_output"
    ],
    "raw_files": [
      "run.2333166.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 51431.6,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 6824.4,
        "unexplained_share": 0.13268885276755923
      },
      {
        "calls": 1,
        "instructions_per_call": 238934.0,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 1,
          "finished_requests": 1,
          "prefill_text_tokens": 9
        },
        "unexplained_instructions_per_call": 45982.0,
        "unexplained_share": 0.1924464496471829
      },
      {
        "calls": 1,
        "instructions_per_call": 35570.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 5042.0,
        "unexplained_share": 0.1417486646050042
      },
      {
        "calls": 1,
        "instructions_per_call": 113118.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_text_tokens": 20
        },
        "unexplained_instructions_per_call": 46773.0,
        "unexplained_share": 0.41348856945844165
      },
      {
        "calls": 4,
        "instructions_per_call": 73282.75,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 13590.25,
        "unexplained_share": 0.18544950892263187
      },
      {
        "calls": 2,
        "instructions_per_call": 97210.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 11689.5,
        "unexplained_share": 0.12024997428248123
      },
      {
        "calls": 2,
        "instructions_per_call": 80776.5,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 10318.5,
        "unexplained_share": 0.1277413604204193
      },
      {
        "calls": 1,
        "instructions_per_call": 270292.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 63
        },
        "unexplained_instructions_per_call": 107366.0,
        "unexplained_share": 0.39722226333002825
      },
      {
        "calls": 1,
        "instructions_per_call": 112464.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 13020.0,
        "unexplained_share": 0.1157703798548869
      },
      {
        "calls": 1,
        "instructions_per_call": 342765.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 84
        },
        "unexplained_instructions_per_call": 139232.0,
        "unexplained_share": 0.40620250025527693
      },
      {
        "calls": 2,
        "instructions_per_call": 126973.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 15451.5,
        "unexplained_share": 0.1216912256936514
      },
      {
        "calls": 1,
        "instructions_per_call": 109487.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 14592.0,
        "unexplained_share": 0.13327609670554494
      },
      {
        "calls": 1,
        "instructions_per_call": 141703.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 17223.0,
        "unexplained_share": 0.12154294545634178
      },
      {
        "calls": 1,
        "instructions_per_call": 752660.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 225
        },
        "unexplained_instructions_per_call": 321271.0,
        "unexplained_share": 0.4268474477187575
      },
      {
        "calls": 1,
        "instructions_per_call": 832278.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_text_tokens": 270
        },
        "unexplained_instructions_per_call": 360922.0,
        "unexplained_share": 0.43365558142832084
      },
      {
        "calls": 1,
        "instructions_per_call": 156927.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 0
        },
        "unexplained_instructions_per_call": 19537.0,
        "unexplained_share": 0.12449737776163439
      },
      {
        "calls": 1,
        "instructions_per_call": 1027016.0,
        "state": {
          "batch_size": 7,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 315
        },
        "unexplained_instructions_per_call": 447397.0,
        "unexplained_share": 0.43562807200666787
      },
      {
        "calls": 1,
        "instructions_per_call": 1176233.0,
        "state": {
          "batch_size": 8,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_text_tokens": 368
        },
        "unexplained_instructions_per_call": 518218.0,
        "unexplained_share": 0.44057427397462917
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 44.05742739746292,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 44.05742739746292,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17"
  }
}