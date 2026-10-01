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

This is iteration 2. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "With fixed head width and CPU execution settings, instruction count should be explained by a fixed dispatch cost plus attention-pair work and linear query/key/value processing.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * key.shape[1]",
        "name": "attention_pairs",
        "rationale": "Tracks attention-score and softmax work across batches, heads, and query-key pairs; head width is fixed in this workload."
      },
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks query processing, per-query overhead, and output writes."
      },
      {
        "expression": "key.numel() + value.numel()",
        "name": "key_value_elements",
        "rationale": "Tracks key/value preparation and memory work as self-attention and cross-attention lengths vary."
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
        "attention_pairs": 3.9335947565347915,
        "key_value_elements": -7.294106614018565,
        "query_elements": 28.056447358480735
      },
      "constant": 118470.35001132598,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 14.917966379784048,
    "max_unexplained_share": 0.4708100953439883,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "attention_pairs",
      "query_elements",
      "key_value_elements"
    ],
    "raw_files": [
      "run.1564770.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142359.0,
        "state": {
          "attention_pairs": 144,
          "key_value_elements": 256,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 17959.0,
        "unexplained_share": 0.12615289514537192
      },
      {
        "calls": 3,
        "instructions_per_call": 164603.0,
        "state": {
          "attention_pairs": 324,
          "key_value_elements": 576,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 33511.666666666664,
        "unexplained_share": 0.20359086205395202
      },
      {
        "calls": 3,
        "instructions_per_call": 168121.66666666666,
        "state": {
          "attention_pairs": 384,
          "key_value_elements": 384,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 37698.33333333333,
        "unexplained_share": 0.22423245070534234
      },
      {
        "calls": 3,
        "instructions_per_call": 195227.0,
        "state": {
          "attention_pairs": 512,
          "key_value_elements": 256,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 49871.666666666664,
        "unexplained_share": 0.2554547612096004
      },
      {
        "calls": 3,
        "instructions_per_call": 191425.33333333334,
        "state": {
          "attention_pairs": 648,
          "key_value_elements": 576,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 58690.66666666667,
        "unexplained_share": 0.3065982210644359
      },
      {
        "calls": 3,
        "instructions_per_call": 201331.66666666666,
        "state": {
          "attention_pairs": 648,
          "key_value_elements": 384,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 60027.33333333333,
        "unexplained_share": 0.29815147476386394
      },
      {
        "calls": 3,
        "instructions_per_call": 143813.33333333334,
        "state": {
          "attention_pairs": 1024,
          "key_value_elements": 1024,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 14256.666666666668,
        "unexplained_share": 0.09913313554607825
      },
      {
        "calls": 3,
        "instructions_per_call": 160774.66666666666,
        "state": {
          "attention_pairs": 1296,
          "key_value_elements": 1152,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 29089.333333333336,
        "unexplained_share": 0.1809323193537954
      },
      {
        "calls": 3,
        "instructions_per_call": 319579.6666666667,
        "state": {
          "attention_pairs": 1728,
          "key_value_elements": 576,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 150461.33333333334,
        "unexplained_share": 0.4708100953439883
      },
      {
        "calls": 3,
        "instructions_per_call": 255576.33333333334,
        "state": {
          "attention_pairs": 2916,
          "key_value_elements": 1728,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 116628.66666666666,
        "unexplained_share": 0.45633594138215716
      },
      {
        "calls": 3,
        "instructions_per_call": 177992.33333333334,
        "state": {
          "attention_pairs": 4096,
          "key_value_elements": 2048,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 34923.0,
        "unexplained_share": 0.19620507999408213
      },
      {
        "calls": 3,
        "instructions_per_call": 247379.33333333334,
        "state": {
          "attention_pairs": 9216,
          "key_value_elements": 3072,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 71621.33333333334,
        "unexplained_share": 0.2895202778997976
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 47.08100953439883,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 47.08100953439883,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}