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
    "hypothesis": "The remaining work may follow products of block counts and remainders rather than rounded matrix area. These features distinguish complete query-block processing from per-row key-tail processing.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks linear query and output processing."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "key_tail_pairs",
        "rationale": "Tracks key-axis scalar remainder work across all query rows."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * (query.shape[1] // 8) * key.shape[1]",
        "name": "query_blocks_times_keys",
        "rationale": "Tests matrix-kernel loops operating on complete eight-row query blocks."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * (query.shape[1] // 8) * (key.shape[1] % 16)",
        "name": "query_blocks_times_key_tail",
        "rationale": "Captures the interaction between complete query blocks and partial key vectors, which separate remainder features cannot express."
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
        "key_tail_pairs": -19.915043781408453,
        "query_blocks_times_key_tail": 528.7417046758246,
        "query_blocks_times_keys": 10.938646352000815,
        "query_elements": 27.015605408651876
      },
      "constant": 117001.57957115077,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.061971972230822,
    "max_unexplained_share": 0.27769655161272083,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "key_tail_pairs",
      "query_blocks_times_keys",
      "query_blocks_times_key_tail"
    ],
    "raw_files": [
      "run.1567755.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142353.66666666666,
        "state": {
          "key_tail_pairs": 144,
          "query_blocks_times_key_tail": 16,
          "query_blocks_times_keys": 16,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 10487.0,
        "unexplained_share": 0.0736686328182625
      },
      {
        "calls": 3,
        "instructions_per_call": 164477.66666666666,
        "state": {
          "key_tail_pairs": 324,
          "query_blocks_times_key_tail": 36,
          "query_blocks_times_keys": 36,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 19103.333333333332,
        "unexplained_share": 0.11614545439806417
      },
      {
        "calls": 3,
        "instructions_per_call": 144009.66666666666,
        "state": {
          "key_tail_pairs": 0,
          "query_blocks_times_key_tail": 0,
          "query_blocks_times_keys": 128,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 11516.0,
        "unexplained_share": 0.0799668540769254
      },
      {
        "calls": 3,
        "instructions_per_call": 168600.66666666666,
        "state": {
          "key_tail_pairs": 384,
          "query_blocks_times_key_tail": 48,
          "query_blocks_times_keys": 48,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 21508.0,
        "unexplained_share": 0.12756770435862255
      },
      {
        "calls": 3,
        "instructions_per_call": 160935.0,
        "state": {
          "key_tail_pairs": 144,
          "query_blocks_times_key_tail": 16,
          "query_blocks_times_keys": 144,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 21368.333333333332,
        "unexplained_share": 0.13277617257484906
      },
      {
        "calls": 3,
        "instructions_per_call": 191551.66666666666,
        "state": {
          "key_tail_pairs": 648,
          "query_blocks_times_key_tail": 72,
          "query_blocks_times_keys": 72,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 32724.666666666664,
        "unexplained_share": 0.1708398952414927
      },
      {
        "calls": 3,
        "instructions_per_call": 201571.33333333334,
        "state": {
          "key_tail_pairs": 648,
          "query_blocks_times_key_tail": 72,
          "query_blocks_times_keys": 72,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 34186.333333333336,
        "unexplained_share": 0.16959918242342661
      },
      {
        "calls": 3,
        "instructions_per_call": 255657.0,
        "state": {
          "key_tail_pairs": 1188,
          "query_blocks_times_key_tail": 132,
          "query_blocks_times_keys": 324,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 70017.0,
        "unexplained_share": 0.2738708503972119
      },
      {
        "calls": 3,
        "instructions_per_call": 178199.33333333334,
        "state": {
          "key_tail_pairs": 0,
          "query_blocks_times_key_tail": 0,
          "query_blocks_times_keys": 512,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 31919.0,
        "unexplained_share": 0.17911963755943716
      },
      {
        "calls": 3,
        "instructions_per_call": 195561.33333333334,
        "state": {
          "key_tail_pairs": 512,
          "query_blocks_times_key_tail": 64,
          "query_blocks_times_keys": 64,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 29204.666666666664,
        "unexplained_share": 0.14933763320629162
      },
      {
        "calls": 3,
        "instructions_per_call": 247594.0,
        "state": {
          "key_tail_pairs": 0,
          "query_blocks_times_key_tail": 0,
          "query_blocks_times_keys": 1152,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 68756.0,
        "unexplained_share": 0.27769655161272083
      },
      {
        "calls": 3,
        "instructions_per_call": 319638.6666666667,
        "state": {
          "key_tail_pairs": 1728,
          "query_blocks_times_key_tail": 216,
          "query_blocks_times_keys": 216,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 84137.33333333334,
        "unexplained_share": 0.26322639313558227
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 27.769655161272084,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 27.769655161272084,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}