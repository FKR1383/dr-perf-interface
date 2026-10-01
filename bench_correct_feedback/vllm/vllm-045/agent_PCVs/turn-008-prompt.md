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

This is iteration 7. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Complementary indicators reduced unexplained cost, suggesting sensitivity to baseline attribution. Shifting the block and regime features away from zero preserves their information while testing whether short-state cost attribution improves.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "len(prompt['prompt_token_ids'])",
        "name": "prompt_tokens",
        "rationale": "Captures token-dependent admission work and preserves eight observed states."
      },
      {
        "expression": "1 + len(prompt['prompt_token_ids']) // 16",
        "name": "token_block_extent",
        "rationale": "Represents fixed setup plus complete token blocks, remaining nonzero for short prompts."
      },
      {
        "expression": "1 + int(len(prompt['prompt_token_ids']) != 10)",
        "name": "ten_token_regime_basis",
        "rationale": "Separates the exceptional ten-token state with a nonzero baseline."
      },
      {
        "expression": "1 + int(len(prompt['prompt_token_ids']) != 9)",
        "name": "nine_token_regime_basis",
        "rationale": "Separates the elevated nine-token state with a nonzero baseline."
      }
    ]
  },
  "case_id": "vllm-045",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-045",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "nine_token_regime_basis": -43804.960508428456,
        "prompt_tokens": -351.48213703098213,
        "ten_token_regime_basis": -46465324.86498105,
        "token_block_extent": 15052.623735725701
      },
      "constant": 93506893.4041852,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 123.15487418929115,
    "max_unexplained_share": 0.11470540377565573,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "token_block_extent",
      "ten_token_regime_basis",
      "nine_token_regime_basis"
    ],
    "raw_files": [
      "run.2313720.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 626858.0,
        "state": {
          "nine_token_regime_basis": 1,
          "prompt_tokens": 9,
          "ten_token_regime_basis": 2,
          "token_block_extent": 1
        },
        "unexplained_instructions_per_call": 71904.0,
        "unexplained_share": 0.11470540377565573
      },
      {
        "calls": 1,
        "instructions_per_call": 48689929.0,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 10,
          "ten_token_regime_basis": 1,
          "token_block_extent": 1
        },
        "unexplained_instructions_per_call": 1723374.0,
        "unexplained_share": 0.03539487601224475
      },
      {
        "calls": 1,
        "instructions_per_call": 531971.0,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 11,
          "ten_token_regime_basis": 2,
          "token_block_extent": 1
        },
        "unexplained_instructions_per_call": 35411.0,
        "unexplained_share": 0.06656565865432514
      },
      {
        "calls": 4,
        "instructions_per_call": 547309.0,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 21,
          "ten_token_regime_basis": 2,
          "token_block_extent": 2
        },
        "unexplained_instructions_per_call": 38275.5,
        "unexplained_share": 0.06993398610291444
      },
      {
        "calls": 3,
        "instructions_per_call": 559301.3333333334,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 22,
          "ten_token_regime_basis": 2,
          "token_block_extent": 2
        },
        "unexplained_instructions_per_call": 44830.33333333332,
        "unexplained_share": 0.08015416853407582
      },
      {
        "calls": 10,
        "instructions_per_call": 549471.9,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 2,
          "token_block_extent": 3
        },
        "unexplained_instructions_per_call": 35463.3,
        "unexplained_share": 0.06454069807755411
      },
      {
        "calls": 12,
        "instructions_per_call": 552908.6666666666,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 2,
          "token_block_extent": 3
        },
        "unexplained_instructions_per_call": 37227.16666666666,
        "unexplained_share": 0.06732968555385277
      },
      {
        "calls": 4,
        "instructions_per_call": 548515.0,
        "state": {
          "nine_token_regime_basis": 2,
          "prompt_tokens": 47,
          "ten_token_regime_basis": 2,
          "token_block_extent": 3
        },
        "unexplained_instructions_per_call": 34899.5,
        "unexplained_share": 0.06362542501116651
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 11.470540377565573,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 11.470540377565573,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}