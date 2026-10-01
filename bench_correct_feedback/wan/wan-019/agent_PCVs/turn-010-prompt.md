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
    "hypothesis": "Two unresolved effects may be mixed: an eight-element cleanup path within 16-element vector remainders, and key processing repeated per query block. These features test both directly.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks linear query and output processing."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "key_remainder_16",
        "rationale": "Tracks remainder processing after full 16-element key vectors."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 8)",
        "name": "key_remainder_8",
        "rationale": "Tests whether eight-element vectors handle part of the 16-element remainder, leaving a separate scalar tail."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * ((query.shape[1] + 31) // 32) * key.shape[1]",
        "name": "keys_per_query_block",
        "rationale": "Tracks key processing repeated for each 32-row query block, including the interaction omitted by a standalone query-block count."
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
        "key_remainder_16": 37.18054614229852,
        "key_remainder_8": -0.3778085784393808,
        "keys_per_query_block": 20.613506212824877,
        "query_elements": 27.450374357173033
      },
      "constant": 118927.30644588388,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.101059374865144,
    "max_unexplained_share": 0.28165896532781853,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "key_remainder_16",
      "key_remainder_8",
      "keys_per_query_block"
    ],
    "raw_files": [
      "run.1568706.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142353.66666666666,
        "state": {
          "key_remainder_16": 144,
          "key_remainder_8": 144,
          "keys_per_query_block": 16,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 11343.0,
        "unexplained_share": 0.07968182531301149
      },
      {
        "calls": 3,
        "instructions_per_call": 164488.33333333334,
        "state": {
          "key_remainder_16": 324,
          "key_remainder_8": 36,
          "keys_per_query_block": 36,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 19875.333333333332,
        "unexplained_share": 0.12083126462869706
      },
      {
        "calls": 3,
        "instructions_per_call": 144009.66666666666,
        "state": {
          "key_remainder_16": 0,
          "key_remainder_8": 0,
          "keys_per_query_block": 64,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 12328.0,
        "unexplained_share": 0.08560536445470096
      },
      {
        "calls": 3,
        "instructions_per_call": 168600.66666666666,
        "state": {
          "key_remainder_16": 384,
          "key_remainder_8": 384,
          "keys_per_query_block": 24,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 22448.0,
        "unexplained_share": 0.13314300852902916
      },
      {
        "calls": 3,
        "instructions_per_call": 160935.0,
        "state": {
          "key_remainder_16": 144,
          "key_remainder_8": 144,
          "keys_per_query_block": 72,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 21972.333333333332,
        "unexplained_share": 0.1365292405836725
      },
      {
        "calls": 3,
        "instructions_per_call": 191551.66666666666,
        "state": {
          "key_remainder_16": 648,
          "key_remainder_8": 72,
          "keys_per_query_block": 36,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 33712.666666666664,
        "unexplained_share": 0.17599777257658944
      },
      {
        "calls": 3,
        "instructions_per_call": 201571.33333333334,
        "state": {
          "key_remainder_16": 648,
          "key_remainder_8": 648,
          "keys_per_query_block": 24,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 35390.333333333336,
        "unexplained_share": 0.17557225399114293
      },
      {
        "calls": 3,
        "instructions_per_call": 255657.0,
        "state": {
          "key_remainder_16": 1188,
          "key_remainder_8": 324,
          "keys_per_query_block": 108,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 70819.0,
        "unexplained_share": 0.2770078660079716
      },
      {
        "calls": 3,
        "instructions_per_call": 178199.33333333334,
        "state": {
          "key_remainder_16": 0,
          "key_remainder_8": 0,
          "keys_per_query_block": 128,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 32987.0,
        "unexplained_share": 0.18511292597428347
      },
      {
        "calls": 3,
        "instructions_per_call": 195561.33333333334,
        "state": {
          "key_remainder_16": 512,
          "key_remainder_8": 512,
          "keys_per_query_block": 16,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 30528.666666666664,
        "unexplained_share": 0.1561078877214991
      },
      {
        "calls": 3,
        "instructions_per_call": 247576.0,
        "state": {
          "key_remainder_16": 0,
          "key_remainder_8": 0,
          "keys_per_query_block": 384,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 69732.0,
        "unexplained_share": 0.28165896532781853
      },
      {
        "calls": 3,
        "instructions_per_call": 319631.0,
        "state": {
          "key_remainder_16": 1728,
          "key_remainder_8": 192,
          "keys_per_query_block": 72,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 86401.33333333334,
        "unexplained_share": 0.2703158746596336
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 28.165896532781854,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 28.165896532781854,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}