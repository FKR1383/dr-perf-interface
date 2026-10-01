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
    "hypothesis": "Matrix-kernel work may scale with the product of rounded tile counts. This captures a joint boundary effect that separate linear remainder terms cannot represent, while retaining scalar key-tail and query-block costs.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks linear query and output processing."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "key_tail_pairs",
        "rationale": "Retains the key-remainder feature that substantially reduced unexplained work."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * ((query.shape[1] + 15) // 16) * ((key.shape[1] + 15) // 16)",
        "name": "matrix_tiles",
        "rationale": "Tests matrix multiplication work counted in full or partial 16-by-16 tiles instead of individual attention pairs."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * ((query.shape[1] + 31) // 32)",
        "name": "query_tiles",
        "rationale": "Tracks setup and dispatch work for 32-row query blocks."
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
        "key_tail_pairs": 36.81182110048565,
        "matrix_tiles": 59.863148143371966,
        "query_elements": 25.89624895470278,
        "query_tiles": 2994.55088875389
      },
      "constant": 108957.4851740857,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.065860623959452,
    "max_unexplained_share": 0.27179076907066296,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "key_tail_pairs",
      "matrix_tiles",
      "query_tiles"
    ],
    "raw_files": [
      "run.1567274.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142715.0,
        "state": {
          "key_tail_pairs": 144,
          "matrix_tiles": 4,
          "query_elements": 288,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 10130.333333333334,
        "unexplained_share": 0.07098296137990634
      },
      {
        "calls": 3,
        "instructions_per_call": 164824.33333333334,
        "state": {
          "key_tail_pairs": 324,
          "matrix_tiles": 4,
          "query_elements": 288,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 18746.0,
        "unexplained_share": 0.1137332068687269
      },
      {
        "calls": 3,
        "instructions_per_call": 143905.33333333334,
        "state": {
          "key_tail_pairs": 0,
          "matrix_tiles": 4,
          "query_elements": 512,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 11194.333333333332,
        "unexplained_share": 0.07778956536241416
      },
      {
        "calls": 3,
        "instructions_per_call": 168922.0,
        "state": {
          "key_tail_pairs": 384,
          "matrix_tiles": 4,
          "query_elements": 512,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 21425.333333333336,
        "unexplained_share": 0.12683565985089768
      },
      {
        "calls": 3,
        "instructions_per_call": 160903.33333333334,
        "state": {
          "key_tail_pairs": 144,
          "matrix_tiles": 16,
          "query_elements": 576,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 20734.333333333332,
        "unexplained_share": 0.12886204967786039
      },
      {
        "calls": 3,
        "instructions_per_call": 191661.0,
        "state": {
          "key_tail_pairs": 648,
          "matrix_tiles": 8,
          "query_elements": 576,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 32492.666666666664,
        "unexplained_share": 0.16953196877125062
      },
      {
        "calls": 3,
        "instructions_per_call": 201551.66666666666,
        "state": {
          "key_tail_pairs": 648,
          "matrix_tiles": 8,
          "query_elements": 864,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 34229.0,
        "unexplained_share": 0.16982742224905112
      },
      {
        "calls": 3,
        "instructions_per_call": 256240.0,
        "state": {
          "key_tail_pairs": 1188,
          "matrix_tiles": 16,
          "query_elements": 864,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 69643.66666666667,
        "unexplained_share": 0.27179076907066296
      },
      {
        "calls": 3,
        "instructions_per_call": 178046.66666666666,
        "state": {
          "key_tail_pairs": 0,
          "matrix_tiles": 16,
          "query_elements": 1024,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 31823.0,
        "unexplained_share": 0.17873403976485566
      },
      {
        "calls": 3,
        "instructions_per_call": 195633.66666666666,
        "state": {
          "key_tail_pairs": 512,
          "matrix_tiles": 8,
          "query_elements": 1024,
          "query_tiles": 4
        },
        "unexplained_instructions_per_call": 29465.0,
        "unexplained_share": 0.15061313577588042
      },
      {
        "calls": 3,
        "instructions_per_call": 247332.0,
        "state": {
          "key_tail_pairs": 0,
          "matrix_tiles": 36,
          "query_elements": 1536,
          "query_tiles": 8
        },
        "unexplained_instructions_per_call": 66137.0,
        "unexplained_share": 0.267401711060437
      },
      {
        "calls": 3,
        "instructions_per_call": 319953.0,
        "state": {
          "key_tail_pairs": 1728,
          "matrix_tiles": 12,
          "query_elements": 1536,
          "query_tiles": 8
        },
        "unexplained_instructions_per_call": 83173.66666666666,
        "unexplained_share": 0.25995588935458225
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 27.179076907066296,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 27.179076907066296,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}