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

This is iteration 10. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "An explicit constant worsened attribution. Active request cardinality adds an independent entry-state dimension that may explain initialization and container-growth costs hidden within the previous prompt-size states.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "len(prompt['prompt_token_ids'])",
        "name": "prompt_tokens",
        "rationale": "Captures token-dependent input and detokenizer setup."
      },
      {
        "expression": "1 + len(self.output_processor.request_states)",
        "name": "active_request_extent",
        "rationale": "Captures admission-state size, including empty-to-nonempty transitions and request-table growth."
      },
      {
        "expression": "16 + int(len(prompt['prompt_token_ids']) != 10)",
        "name": "ten_token_regime_basis",
        "rationale": "Retains the exceptional ten-token regime using the previously better-performing positive basis."
      },
      {
        "expression": "16 + int(len(prompt['prompt_token_ids']) != 9)",
        "name": "nine_token_regime_basis",
        "rationale": "Retains separation of the elevated nine-token state."
      }
    ]
  },
  "case_id": "vllm-045",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-045",
    "distinct_states": 28,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_request_extent": 9.699555415860365,
        "nine_token_regime_basis": -32663.748221568796,
        "prompt_tokens": 453.87381327466136,
        "ten_token_regime_basis": -44439183.1244566
      },
      "constant": 756477963.4886605,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 128.65517716109753,
    "max_unexplained_share": 0.20499246233568372,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "active_request_extent",
      "ten_token_regime_basis",
      "nine_token_regime_basis"
    ],
    "raw_files": [
      "run.2316031.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 624862.0,
        "state": {
          "active_request_extent": 1,
          "nine_token_regime_basis": 16,
          "prompt_tokens": 9,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 128092.0,
        "unexplained_share": 0.20499246233568372
      },
      {
        "calls": 1,
        "instructions_per_call": 48696587.0,
        "state": {
          "active_request_extent": 1,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 10,
          "ten_token_regime_basis": 16
        },
        "unexplained_instructions_per_call": 3792757.0,
        "unexplained_share": 0.07788547891456951
      },
      {
        "calls": 1,
        "instructions_per_call": 531075.0,
        "state": {
          "active_request_extent": 2,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 11,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 70164.0,
        "unexplained_share": 0.13211693263663324
      },
      {
        "calls": 1,
        "instructions_per_call": 555797.0,
        "state": {
          "active_request_extent": 1,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 21,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 88256.0,
        "unexplained_share": 0.15879178908846214
      },
      {
        "calls": 1,
        "instructions_per_call": 544835.0,
        "state": {
          "active_request_extent": 2,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 21,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 78921.0,
        "unexplained_share": 0.1448530288986574
      },
      {
        "calls": 1,
        "instructions_per_call": 543539.0,
        "state": {
          "active_request_extent": 3,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 21,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 78877.0,
        "unexplained_share": 0.1451174616724835
      },
      {
        "calls": 1,
        "instructions_per_call": 543741.0,
        "state": {
          "active_request_extent": 4,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 21,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 77250.0,
        "unexplained_share": 0.142071317042489
      },
      {
        "calls": 1,
        "instructions_per_call": 567307.0,
        "state": {
          "active_request_extent": 1,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 22,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 100117.0,
        "unexplained_share": 0.1764776390913562
      },
      {
        "calls": 1,
        "instructions_per_call": 561156.0,
        "state": {
          "active_request_extent": 2,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 22,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 92332.0,
        "unexplained_share": 0.16453891609463323
      },
      {
        "calls": 1,
        "instructions_per_call": 546591.0,
        "state": {
          "active_request_extent": 3,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 22,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 79102.0,
        "unexplained_share": 0.14471881168917894
      },
      {
        "calls": 2,
        "instructions_per_call": 553173.5,
        "state": {
          "active_request_extent": 1,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 77056.0,
        "unexplained_share": 0.1392980683275681
      },
      {
        "calls": 1,
        "instructions_per_call": 547572.0,
        "state": {
          "active_request_extent": 2,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 71168.0,
        "unexplained_share": 0.12997012265053728
      },
      {
        "calls": 2,
        "instructions_per_call": 544994.5,
        "state": {
          "active_request_extent": 3,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 68489.0,
        "unexplained_share": 0.12566915812911875
      },
      {
        "calls": 1,
        "instructions_per_call": 545666.0,
        "state": {
          "active_request_extent": 4,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 70329.0,
        "unexplained_share": 0.12888653498660352
      },
      {
        "calls": 2,
        "instructions_per_call": 547088.0,
        "state": {
          "active_request_extent": 5,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 70925.0,
        "unexplained_share": 0.12964093527915072
      },
      {
        "calls": 1,
        "instructions_per_call": 547659.0,
        "state": {
          "active_request_extent": 6,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 69552.0,
        "unexplained_share": 0.12699873461405728
      },
      {
        "calls": 1,
        "instructions_per_call": 544818.0,
        "state": {
          "active_request_extent": 7,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 45,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 68336.0,
        "unexplained_share": 0.12542904235909974
      },
      {
        "calls": 2,
        "instructions_per_call": 556130.0,
        "state": {
          "active_request_extent": 1,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 78695.5,
        "unexplained_share": 0.14150558322694334
      },
      {
        "calls": 2,
        "instructions_per_call": 552397.0,
        "state": {
          "active_request_extent": 2,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 75494.5,
        "unexplained_share": 0.13666710717111064
      },
      {
        "calls": 2,
        "instructions_per_call": 544952.0,
        "state": {
          "active_request_extent": 3,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 69029.0,
        "unexplained_share": 0.1266698718419237
      },
      {
        "calls": 2,
        "instructions_per_call": 548575.0,
        "state": {
          "active_request_extent": 4,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 71124.0,
        "unexplained_share": 0.1296522809096295
      },
      {
        "calls": 2,
        "instructions_per_call": 549928.0,
        "state": {
          "active_request_extent": 5,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 72837.5,
        "unexplained_share": 0.13244915698055018
      },
      {
        "calls": 1,
        "instructions_per_call": 559404.0,
        "state": {
          "active_request_extent": 6,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 82325.0,
        "unexplained_share": 0.14716555476900414
      },
      {
        "calls": 1,
        "instructions_per_call": 547385.0,
        "state": {
          "active_request_extent": 7,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 46,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 70498.0,
        "unexplained_share": 0.1287905222101446
      },
      {
        "calls": 1,
        "instructions_per_call": 542850.0,
        "state": {
          "active_request_extent": 2,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 47,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 67077.0,
        "unexplained_share": 0.12356452058579719
      },
      {
        "calls": 1,
        "instructions_per_call": 546423.0,
        "state": {
          "active_request_extent": 4,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 47,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 67229.0,
        "unexplained_share": 0.12303471852392743
      },
      {
        "calls": 1,
        "instructions_per_call": 547031.0,
        "state": {
          "active_request_extent": 6,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 47,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 69671.0,
        "unexplained_share": 0.12736206906007155
      },
      {
        "calls": 1,
        "instructions_per_call": 545660.0,
        "state": {
          "active_request_extent": 8,
          "nine_token_regime_basis": 17,
          "prompt_tokens": 47,
          "ten_token_regime_basis": 17
        },
        "unexplained_instructions_per_call": 68705.0,
        "unexplained_share": 0.12591173991130009
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 20.49924623356837,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 20.49924623356837,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}