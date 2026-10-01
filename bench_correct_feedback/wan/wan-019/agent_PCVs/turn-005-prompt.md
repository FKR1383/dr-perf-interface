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

This is iteration 5. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The remaining growth may reflect discrete query blocking rather than quadratic query work. A 32-row tile count captures the extra block at length 48 while preserving linear, pairwise, and key-remainder costs.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * key.shape[1]",
        "name": "attention_pairs",
        "rationale": "Tracks attention matrix arithmetic."
      },
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks per-query processing and output work."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "scalar_tail_pairs",
        "rationale": "Tracks scalar remainder processing along the key dimension."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * ((query.shape[1] + 31) // 32)",
        "name": "query_tiles",
        "rationale": "Models per-tile overhead for 32-row CPU attention blocks, including the additional block at query length 48."
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
        "attention_pairs": 0.0487153544057094,
        "query_elements": 26.741913417786883,
        "query_tiles": 2918.0797779004233,
        "scalar_tail_pairs": 37.162790867908335
      },
      "constant": 109462.22204114494,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.057441957294941,
    "max_unexplained_share": 0.27099494514907446,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "attention_pairs",
      "query_elements",
      "scalar_tail_pairs",
      "query_tiles"
    ],
    "raw_files": [
      "run.1566374.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142987.33333333334,
        "state": {
          "attention_pairs": 144,
          "query_elements": 288,
          "query_tiles": 4,
          "scalar_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 9978.666666666666,
        "unexplained_share": 0.06978706738592229
      },
      {
        "calls": 3,
        "instructions_per_call": 164807.66666666666,
        "state": {
          "attention_pairs": 324,
          "query_elements": 288,
          "query_tiles": 4,
          "scalar_tail_pairs": 324
        },
        "unexplained_instructions_per_call": 18518.333333333336,
        "unexplained_share": 0.11236330025099966
      },
      {
        "calls": 3,
        "instructions_per_call": 168752.33333333334,
        "state": {
          "attention_pairs": 384,
          "query_elements": 512,
          "query_tiles": 4,
          "scalar_tail_pairs": 384
        },
        "unexplained_instructions_per_call": 20900.666666666664,
        "unexplained_share": 0.12385408991875665
      },
      {
        "calls": 3,
        "instructions_per_call": 195313.33333333334,
        "state": {
          "attention_pairs": 512,
          "query_elements": 1024,
          "query_tiles": 4,
          "scalar_tail_pairs": 512
        },
        "unexplained_instructions_per_call": 28276.0,
        "unexplained_share": 0.14477250230399016
      },
      {
        "calls": 3,
        "instructions_per_call": 191627.33333333334,
        "state": {
          "attention_pairs": 648,
          "query_elements": 576,
          "query_tiles": 4,
          "scalar_tail_pairs": 648
        },
        "unexplained_instructions_per_call": 31898.0,
        "unexplained_share": 0.16645850800686052
      },
      {
        "calls": 3,
        "instructions_per_call": 201184.33333333334,
        "state": {
          "attention_pairs": 648,
          "query_elements": 864,
          "query_tiles": 4,
          "scalar_tail_pairs": 648
        },
        "unexplained_instructions_per_call": 33257.0,
        "unexplained_share": 0.16530611230496742
      },
      {
        "calls": 3,
        "instructions_per_call": 143942.66666666666,
        "state": {
          "attention_pairs": 1024,
          "query_elements": 512,
          "query_tiles": 4,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 11201.666666666668,
        "unexplained_share": 0.07782033587446856
      },
      {
        "calls": 3,
        "instructions_per_call": 161045.0,
        "state": {
          "attention_pairs": 1296,
          "query_elements": 576,
          "query_tiles": 4,
          "scalar_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 20766.333333333332,
        "unexplained_share": 0.12894739565545862
      },
      {
        "calls": 3,
        "instructions_per_call": 319739.6666666667,
        "state": {
          "attention_pairs": 1728,
          "query_elements": 1536,
          "query_tiles": 8,
          "scalar_tail_pairs": 1728
        },
        "unexplained_instructions_per_call": 81382.66666666666,
        "unexplained_share": 0.2545279023872546
      },
      {
        "calls": 3,
        "instructions_per_call": 256057.66666666666,
        "state": {
          "attention_pairs": 2916,
          "query_elements": 864,
          "query_tiles": 4,
          "scalar_tail_pairs": 1188
        },
        "unexplained_instructions_per_call": 69390.33333333333,
        "unexplained_share": 0.27099494514907446
      },
      {
        "calls": 3,
        "instructions_per_call": 178020.33333333334,
        "state": {
          "attention_pairs": 4096,
          "query_elements": 1024,
          "query_tiles": 4,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 31830.333333333332,
        "unexplained_share": 0.17880167246812628
      },
      {
        "calls": 3,
        "instructions_per_call": 247436.66666666666,
        "state": {
          "attention_pairs": 9216,
          "query_elements": 1536,
          "query_tiles": 8,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 66144.33333333333,
        "unexplained_share": 0.26731823631636376
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 27.099494514907445,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 27.099494514907445,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}