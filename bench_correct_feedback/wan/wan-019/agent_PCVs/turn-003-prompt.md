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

This is iteration 3. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "CPU attention has substantial per-row scalar tail costs for key lengths not divisible by 16. Adding query-weighted remainder work should explain the nonlinear differences missed by total tensor sizes.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * key.shape[1]",
        "name": "attention_pairs",
        "rationale": "Tracks total attention matrix arithmetic."
      },
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks per-query processing and output work."
      },
      {
        "expression": "key.numel() + value.numel()",
        "name": "key_value_elements",
        "rationale": "Tracks key/value preparation and memory work."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "scalar_tail_pairs",
        "rationale": "Captures scalar remainder processing after 16-element vector blocks; lengths 9 and 27 have disproportionately high instruction counts compared with aligned lengths."
      }
    ]
  },
  "case_id": "wan-019",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-019",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "attention_pairs": 4.977945328561409,
        "key_value_elements": -8.838465486158974,
        "query_elements": 26.865026435182283,
        "scalar_tail_pairs": 40.93241766300947
      },
      "constant": 121120.99276639613,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.071173871867359,
    "max_unexplained_share": 0.27834629278066036,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "attention_pairs",
      "query_elements",
      "key_value_elements",
      "scalar_tail_pairs"
    ],
    "raw_files": [
      "run.1565179.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142617.66666666666,
        "state": {
          "attention_pairs": 144,
          "key_value_elements": 256,
          "query_elements": 288,
          "scalar_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 10012.333333333334,
        "unexplained_share": 0.07020401866996376
      },
      {
        "calls": 3,
        "instructions_per_call": 164787.0,
        "state": {
          "attention_pairs": 324,
          "key_value_elements": 576,
          "query_elements": 288,
          "scalar_tail_pairs": 324
        },
        "unexplained_instructions_per_call": 18180.666666666664,
        "unexplained_share": 0.11032828236855252
      },
      {
        "calls": 3,
        "instructions_per_call": 168705.0,
        "state": {
          "attention_pairs": 384,
          "key_value_elements": 384,
          "query_elements": 512,
          "scalar_tail_pairs": 384
        },
        "unexplained_instructions_per_call": 20090.0,
        "unexplained_share": 0.11908360748051332
      },
      {
        "calls": 3,
        "instructions_per_call": 195477.0,
        "state": {
          "attention_pairs": 512,
          "key_value_elements": 256,
          "query_elements": 1024,
          "scalar_tail_pairs": 512
        },
        "unexplained_instructions_per_call": 26901.333333333336,
        "unexplained_share": 0.1376189185087419
      },
      {
        "calls": 3,
        "instructions_per_call": 191448.0,
        "state": {
          "attention_pairs": 648,
          "key_value_elements": 576,
          "query_elements": 576,
          "scalar_tail_pairs": 648
        },
        "unexplained_instructions_per_call": 30442.333333333336,
        "unexplained_share": 0.15901097600044573
      },
      {
        "calls": 3,
        "instructions_per_call": 201477.66666666666,
        "state": {
          "attention_pairs": 648,
          "key_value_elements": 384,
          "query_elements": 864,
          "scalar_tail_pairs": 648
        },
        "unexplained_instructions_per_call": 31699.0,
        "unexplained_share": 0.15733257449543622
      },
      {
        "calls": 3,
        "instructions_per_call": 143726.66666666666,
        "state": {
          "attention_pairs": 1024,
          "key_value_elements": 1024,
          "query_elements": 512,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 12267.333333333334,
        "unexplained_share": 0.08535182522380445
      },
      {
        "calls": 3,
        "instructions_per_call": 160822.0,
        "state": {
          "attention_pairs": 1296,
          "key_value_elements": 1152,
          "query_elements": 576,
          "scalar_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 21345.333333333332,
        "unexplained_share": 0.13272645119034293
      },
      {
        "calls": 3,
        "instructions_per_call": 319878.6666666667,
        "state": {
          "attention_pairs": 1728,
          "key_value_elements": 576,
          "query_elements": 1536,
          "scalar_tail_pairs": 1728
        },
        "unexplained_instructions_per_call": 77118.66666666666,
        "unexplained_share": 0.24108724558061595
      },
      {
        "calls": 3,
        "instructions_per_call": 255803.0,
        "state": {
          "attention_pairs": 2916,
          "key_value_elements": 1728,
          "query_elements": 864,
          "scalar_tail_pairs": 1188
        },
        "unexplained_instructions_per_call": 66901.66666666667,
        "unexplained_share": 0.2615358954612208
      },
      {
        "calls": 3,
        "instructions_per_call": 177964.33333333334,
        "state": {
          "attention_pairs": 4096,
          "key_value_elements": 2048,
          "query_elements": 1024,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 32963.0,
        "unexplained_share": 0.18522250713157878
      },
      {
        "calls": 3,
        "instructions_per_call": 247395.66666666666,
        "state": {
          "attention_pairs": 9216,
          "key_value_elements": 3072,
          "query_elements": 1536,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 68861.66666666666,
        "unexplained_share": 0.27834629278066036
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 27.834629278066036,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 27.834629278066036,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}