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
    "hypothesis": "A second key-axis blocking period may explain the work left unresolved by 16-element vector remainders. The six-column remainder tests this independently of the unsuccessful query-axis tiling features.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * key.shape[1]",
        "name": "attention_pairs",
        "rationale": "Tracks total attention arithmetic."
      },
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks linear query and output processing."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "key_vector_remainder",
        "rationale": "Tracks the observed sensitivity to key lengths outside complete 16-element vectors."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 6)",
        "name": "key_microkernel_remainder",
        "rationale": "Tests a separate six-column matrix-multiplication blocking effect, allowing matrix kernels and softmax to use different block widths."
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
        "attention_pairs": 0.27838128120530914,
        "key_microkernel_remainder": -0.11445684858440636,
        "key_vector_remainder": 37.11345744680296,
        "query_elements": 28.638534373822193
      },
      "constant": 119297.27120541825,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.071208249311894,
    "max_unexplained_share": 0.2812822174934335,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "attention_pairs",
      "query_elements",
      "key_vector_remainder",
      "key_microkernel_remainder"
    ],
    "raw_files": [
      "run.1568266.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142707.33333333334,
        "state": {
          "attention_pairs": 144,
          "key_microkernel_remainder": 144,
          "key_vector_remainder": 144,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 11556.333333333334,
        "unexplained_share": 0.08097925357725134
      },
      {
        "calls": 3,
        "instructions_per_call": 164829.33333333334,
        "state": {
          "attention_pairs": 324,
          "key_microkernel_remainder": 108,
          "key_vector_remainder": 324,
          "query_elements": 288
        },
        "unexplained_instructions_per_call": 19966.666666666668,
        "unexplained_share": 0.12113539661225348
      },
      {
        "calls": 3,
        "instructions_per_call": 168922.0,
        "state": {
          "attention_pairs": 384,
          "key_microkernel_remainder": 0,
          "key_vector_remainder": 384,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 22599.333333333336,
        "unexplained_share": 0.1337856130837507
      },
      {
        "calls": 3,
        "instructions_per_call": 195633.66666666666,
        "state": {
          "attention_pairs": 512,
          "key_microkernel_remainder": 512,
          "key_vector_remainder": 512,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 30255.0,
        "unexplained_share": 0.154651295533659
      },
      {
        "calls": 3,
        "instructions_per_call": 191661.0,
        "state": {
          "attention_pairs": 648,
          "key_microkernel_remainder": 216,
          "key_vector_remainder": 648,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 33618.666666666664,
        "unexplained_share": 0.17540692507430652
      },
      {
        "calls": 3,
        "instructions_per_call": 201551.66666666666,
        "state": {
          "attention_pairs": 648,
          "key_microkernel_remainder": 0,
          "key_vector_remainder": 648,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 35139.0,
        "unexplained_share": 0.17434239359634834
      },
      {
        "calls": 3,
        "instructions_per_call": 143905.33333333334,
        "state": {
          "attention_pairs": 1024,
          "key_microkernel_remainder": 256,
          "key_vector_remainder": 0,
          "query_elements": 512
        },
        "unexplained_instructions_per_call": 12418.333333333332,
        "unexplained_share": 0.08629515700136199
      },
      {
        "calls": 3,
        "instructions_per_call": 160906.0,
        "state": {
          "attention_pairs": 1296,
          "key_microkernel_remainder": 0,
          "key_vector_remainder": 144,
          "query_elements": 576
        },
        "unexplained_instructions_per_call": 22166.333333333332,
        "unexplained_share": 0.13775952005104428
      },
      {
        "calls": 3,
        "instructions_per_call": 319953.0,
        "state": {
          "attention_pairs": 1728,
          "key_microkernel_remainder": 576,
          "key_vector_remainder": 1728,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 85839.66666666666,
        "unexplained_share": 0.26828836318667637
      },
      {
        "calls": 3,
        "instructions_per_call": 256240.0,
        "state": {
          "attention_pairs": 2916,
          "key_microkernel_remainder": 324,
          "key_vector_remainder": 1188,
          "query_elements": 864
        },
        "unexplained_instructions_per_call": 70877.66666666667,
        "unexplained_share": 0.27660656676032885
      },
      {
        "calls": 3,
        "instructions_per_call": 178046.66666666666,
        "state": {
          "attention_pairs": 4096,
          "key_microkernel_remainder": 256,
          "key_vector_remainder": 0,
          "query_elements": 1024
        },
        "unexplained_instructions_per_call": 32791.0,
        "unexplained_share": 0.18417081663983226
      },
      {
        "calls": 3,
        "instructions_per_call": 247342.33333333334,
        "state": {
          "attention_pairs": 9216,
          "key_microkernel_remainder": 0,
          "key_vector_remainder": 0,
          "query_elements": 1536
        },
        "unexplained_instructions_per_call": 69573.0,
        "unexplained_share": 0.2812822174934335
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 28.128221749343354,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 28.128221749343354,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}