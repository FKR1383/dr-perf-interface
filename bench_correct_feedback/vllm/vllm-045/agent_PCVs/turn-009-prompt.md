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

This is iteration 8. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Positive feature offsets reduced maximum irregularity from 12.26% to 11.47%. A larger offset tests whether improved baseline attribution can bring the remaining nine-token residual below 10%, while preserving the same explanatory state distinctions.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "len(prompt['prompt_token_ids'])",
        "name": "prompt_tokens",
        "rationale": "Captures token-dependent work and distinguishes the observed prompt lengths."
      },
      {
        "expression": "16 + len(prompt['prompt_token_ids']) // 16",
        "name": "token_block_basis",
        "rationale": "Captures block-dependent work with a positive baseline."
      },
      {
        "expression": "16 + int(len(prompt['prompt_token_ids']) != 10)",
        "name": "ten_token_regime_basis",
        "rationale": "Preserves separation of the exceptionally costly ten-token state."
      },
      {
        "expression": "16 + int(len(prompt['prompt_token_ids']) != 9)",
        "name": "nine_token_regime_basis",
        "rationale": "Preserves separation of the elevated nine-token state."
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
        "nine_token_regime_basis": -43343.49028004347,
        "prompt_tokens": -361.9470908102107,
        "ten_token_regime_basis": -46473767.542985365,
        "token_block_basis": 14840.471370309739
      },
      "constant": 791057821.1546601,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 109.72204664768651,
    "max_unexplained_share": 0.1134610103022987,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "token_block_basis",
      "ten_token_regime_basis",
      "nine_token_regime_basis"
    ],
    "raw_files": [
      "run.2314539.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 626268.0,
        "state": {
          "nine_token_regime_basis": 16,
          "prompt_tokens": 9,
          "ten_token_regime_basis": 17,
          "token_block_basis": 16
        },
        "unexplained_instructions_per_call": 71057.0,
        "unexplained_share": 0.1134610103022987
      },
      {
        "calls": 1,
        "instructions_per_call": 48695801.0,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 10,
          "ten_token_regime_basis": 16,
          "token_block_basis": 16
        },
        "unexplained_instructions_per_call": 1720053.0,
        "unexplained_share": 0.035322409010173174
      },
      {
        "calls": 1,
        "instructions_per_call": 532681.0,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 11,
          "ten_token_regime_basis": 17,
          "token_block_basis": 16
        },
        "unexplained_instructions_per_call": 35135.0,
        "unexplained_share": 0.0659588008582998
      },
      {
        "calls": 4,
        "instructions_per_call": 547336.0,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 21,
          "ten_token_regime_basis": 17,
          "token_block_basis": 17
        },
        "unexplained_instructions_per_call": 38243.5,
        "unexplained_share": 0.0698720712688367
      },
      {
        "calls": 3,
        "instructions_per_call": 558492.3333333334,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 22,
          "ten_token_regime_basis": 17,
          "token_block_basis": 17
        },
        "unexplained_instructions_per_call": 44330.333333333336,
        "unexplained_share": 0.07937500783359007
      },
      {
        "calls": 10,
        "instructions_per_call": 548957.8,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17,
          "token_block_basis": 18
        },
        "unexplained_instructions_per_call": 35229.700000000004,
        "unexplained_share": 0.06417560694100713
      },
      {
        "calls": 12,
        "instructions_per_call": 552267.1666666666,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17,
          "token_block_basis": 18
        },
        "unexplained_instructions_per_call": 36743.0,
        "unexplained_share": 0.06653120485465519
      },
      {
        "calls": 4,
        "instructions_per_call": 547949.75,
        "state": {
          "nine_token_regime_basis": 17,
          "prompt_tokens": 47,
          "ten_token_regime_basis": 17,
          "token_block_basis": 18
        },
        "unexplained_instructions_per_call": 34448.5,
        "unexplained_share": 0.0628679910885989
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 11.34610103022987,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 11.34610103022987,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}