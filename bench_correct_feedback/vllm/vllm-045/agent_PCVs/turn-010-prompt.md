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
    "hypothesis": "Offset changes have plateaued. Replacing the block feature with an explicit constant tests whether Dr. Perf can attribute more of the dominant fixed request-setup work, while retaining token scaling and both exceptional-state indicators.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "1",
        "name": "request_setup",
        "rationale": "Explicitly represents fixed per-request setup, which dominates steady-state instruction counts."
      },
      {
        "expression": "len(prompt['prompt_token_ids'])",
        "name": "prompt_tokens",
        "rationale": "Captures token-dependent work and preserves the eight observed states."
      },
      {
        "expression": "int(len(prompt['prompt_token_ids']) == 10)",
        "name": "ten_token_regime",
        "rationale": "Separates the exceptional initialization cost observed in the ten-token state."
      },
      {
        "expression": "int(len(prompt['prompt_token_ids']) == 9)",
        "name": "nine_token_regime",
        "rationale": "Separates the additional setup cost observed in the nine-token state."
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
        "nine_token_regime": 42849.51687522189,
        "prompt_tokens": 438.30854632587864,
        "request_setup": 0.0,
        "ten_token_regime": 45362812.87331386
      },
      "constant": 472387.3008170258,
      "dependent_columns": [
        0
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 98.34106790600345,
    "max_unexplained_share": 0.15563944684931638,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "request_setup",
      "prompt_tokens",
      "ten_token_regime",
      "nine_token_regime"
    ],
    "raw_files": [
      "run.2315276.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 626737.0,
        "state": {
          "nine_token_regime": 1,
          "prompt_tokens": 9,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 97545.0,
        "unexplained_share": 0.15563944684931638
      },
      {
        "calls": 1,
        "instructions_per_call": 48692646.0,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 10,
          "request_setup": 1,
          "ten_token_regime": 1
        },
        "unexplained_instructions_per_call": 2851380.0,
        "unexplained_share": 0.05855874006107616
      },
      {
        "calls": 1,
        "instructions_per_call": 532443.0,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 11,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 58326.0,
        "unexplained_share": 0.10954412021568506
      },
      {
        "calls": 4,
        "instructions_per_call": 547542.75,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 21,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 68056.0,
        "unexplained_share": 0.12429349123881195
      },
      {
        "calls": 3,
        "instructions_per_call": 559453.6666666666,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 22,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 75400.33333333334,
        "unexplained_share": 0.1347749381688445
      },
      {
        "calls": 10,
        "instructions_per_call": 549166.6,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 45,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 60193.20000000001,
        "unexplained_share": 0.10960826823772607
      },
      {
        "calls": 12,
        "instructions_per_call": 553246.4166666666,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 46,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 62685.24999999999,
        "unexplained_share": 0.11330439404864348
      },
      {
        "calls": 4,
        "instructions_per_call": 546574.5,
        "state": {
          "nine_token_regime": 0,
          "prompt_tokens": 47,
          "request_setup": 1,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 56980.25,
        "unexplained_share": 0.1042497408861921
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 15.563944684931638,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 15.563944684931638,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}