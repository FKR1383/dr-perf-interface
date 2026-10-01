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

This is iteration 6. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Token-block boundaries may explain steady-state variation better than text length. Complementary indicators preserve separation of the two exceptional states while testing sensitivity to how the fitted model allocates baseline costs.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "len(prompt['prompt_token_ids'])",
        "name": "prompt_tokens",
        "rationale": "Captures work proportional to prompt token count."
      },
      {
        "expression": "len(prompt['prompt_token_ids']) // 16",
        "name": "complete_token_blocks",
        "rationale": "Tests whether block-based hashing and cache setup explain variation better than character count."
      },
      {
        "expression": "int(len(prompt['prompt_token_ids']) != 10)",
        "name": "outside_ten_token_regime",
        "rationale": "Separates the exceptional ten-token initialization state using the steady-state regime as the active indicator."
      },
      {
        "expression": "int(len(prompt['prompt_token_ids']) != 9)",
        "name": "outside_nine_token_regime",
        "rationale": "Separates the elevated nine-token state using a complementary indicator."
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
        "complete_token_blocks": 16229.264056552247,
        "outside_nine_token_regime": -42910.761963023346,
        "outside_ten_token_regime": -46329163.97589729,
        "prompt_tokens": -453.675611745501
      },
      "constant": 46874242.80916436,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 133.27297145267949,
    "max_unexplained_share": 0.12263966615781255,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "complete_token_blocks",
      "outside_ten_token_regime",
      "outside_nine_token_regime"
    ],
    "raw_files": [
      "run.2312913.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 629519.0,
        "state": {
          "complete_token_blocks": 0,
          "outside_nine_token_regime": 0,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 9
        },
        "unexplained_instructions_per_call": 77204.0,
        "unexplained_share": 0.12263966615781255
      },
      {
        "calls": 1,
        "instructions_per_call": 48677332.0,
        "state": {
          "complete_token_blocks": 0,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 0,
          "prompt_tokens": 10
        },
        "unexplained_instructions_per_call": 1849627.0,
        "unexplained_share": 0.03799770702305541
      },
      {
        "calls": 1,
        "instructions_per_call": 531415.0,
        "state": {
          "complete_token_blocks": 0,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 11
        },
        "unexplained_instructions_per_call": 37540.0,
        "unexplained_share": 0.0706415889653096
      },
      {
        "calls": 4,
        "instructions_per_call": 546088.0,
        "state": {
          "complete_token_blocks": 1,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 21
        },
        "unexplained_instructions_per_call": 39702.0,
        "unexplained_share": 0.07270256808426481
      },
      {
        "calls": 3,
        "instructions_per_call": 558049.0,
        "state": {
          "complete_token_blocks": 1,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 22
        },
        "unexplained_instructions_per_call": 46667.99999999999,
        "unexplained_share": 0.08362706500683631
      },
      {
        "calls": 10,
        "instructions_per_call": 547662.9,
        "state": {
          "complete_token_blocks": 2,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 45
        },
        "unexplained_instructions_per_call": 37303.7,
        "unexplained_share": 0.06811434552167035
      },
      {
        "calls": 12,
        "instructions_per_call": 550559.1666666666,
        "state": {
          "complete_token_blocks": 2,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 46
        },
        "unexplained_instructions_per_call": 38663.99999999999,
        "unexplained_share": 0.07022678458718484
      },
      {
        "calls": 4,
        "instructions_per_call": 545920.0,
        "state": {
          "complete_token_blocks": 2,
          "outside_nine_token_regime": 1,
          "outside_ten_token_regime": 1,
          "prompt_tokens": 47
        },
        "unexplained_instructions_per_call": 36308.5,
        "unexplained_share": 0.06650882913247362
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 12.263966615781255,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 12.263966615781255,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}