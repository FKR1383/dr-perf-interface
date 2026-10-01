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

This is iteration 6. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The nearly zero fitted attention-pair coefficient suggests total pair count does not adequately describe individual matrix-kernel paths. Modeling remainders on both matrix axes may explain work that key remainders and query-tile overhead alone missed.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * key.shape[1]",
        "name": "attention_pairs",
        "rationale": "Tracks total attention matrix work."
      },
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks linear query and output processing."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "key_tail_pairs",
        "rationale": "Captures remainder work along the key dimension."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * (query.shape[1] % 16) * key.shape[1]",
        "name": "query_tail_pairs",
        "rationale": "Captures matrix-kernel remainder work along the query dimension, allowing full vector blocks and partial blocks to have different fitted costs."
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
        "attention_pairs": 1.8412899470892974,
        "key_tail_pairs": 42.7286293437752,
        "query_elements": 25.537257764908798,
        "query_tail_pairs": -4.745303805577399
      },
      "constant": 117271.03124828533,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.080993331968784,
    "max_unexplained_share": 0.2804192353122017,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "attention_pairs",
      "query_elements",
      "key_tail_pairs",
      "query_tail_pairs"
    ],
    "raw_files": [
      "run.1566789.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142465.33333333334,
        "state": {
          "attention_pairs": 144,
          "key_tail_pairs": 144,
          "query_elements": 288,
          "query_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 11057.0,
        "unexplained_share": 0.07761186347087946
      },
      {
        "calls": 3,
        "instructions_per_call": 164833.66666666666,
        "state": {
          "attention_pairs": 324,
          "key_tail_pairs": 324,
          "query_elements": 288,
          "query_tail_pairs": 324
        },
        "unexplained_instructions_per_call": 19680.0,
        "unexplained_share": 0.11939308515048504
      },
      {
        "calls": 3,
        "instructions_per_call": 168522.0,
        "state": {
          "attention_pairs": 384,
          "key_tail_pairs": 384,
          "query_elements": 512,
          "query_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 22007.0,
        "unexplained_share": 0.13058829114299617
      },
      {
        "calls": 3,
        "instructions_per_call": 195300.33333333334,
        "state": {
          "attention_pairs": 512,
          "key_tail_pairs": 512,
          "query_elements": 1024,
          "query_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 29667.0,
        "unexplained_share": 0.15190450263781766
      },
      {
        "calls": 3,
        "instructions_per_call": 191853.0,
        "state": {
          "attention_pairs": 648,
          "key_tail_pairs": 648,
          "query_elements": 576,
          "query_tail_pairs": 72
        },
        "unexplained_instructions_per_call": 33175.666666666664,
        "unexplained_share": 0.17292232421002884
      },
      {
        "calls": 3,
        "instructions_per_call": 201373.33333333334,
        "state": {
          "attention_pairs": 648,
          "key_tail_pairs": 648,
          "query_elements": 864,
          "query_tail_pairs": 264
        },
        "unexplained_instructions_per_call": 34584.333333333336,
        "unexplained_share": 0.17174236906574852
      },
      {
        "calls": 3,
        "instructions_per_call": 143850.0,
        "state": {
          "attention_pairs": 1024,
          "key_tail_pairs": 0,
          "query_elements": 512,
          "query_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 12293.0,
        "unexplained_share": 0.08545707334028502
      },
      {
        "calls": 3,
        "instructions_per_call": 161048.0,
        "state": {
          "attention_pairs": 1296,
          "key_tail_pairs": 144,
          "query_elements": 576,
          "query_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 22166.0,
        "unexplained_share": 0.13763598430281654
      },
      {
        "calls": 3,
        "instructions_per_call": 319714.6666666667,
        "state": {
          "attention_pairs": 1728,
          "key_tail_pairs": 1728,
          "query_elements": 1536,
          "query_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 84266.66666666666,
        "unexplained_share": 0.2635683484440292
      },
      {
        "calls": 3,
        "instructions_per_call": 256162.0,
        "state": {
          "attention_pairs": 2916,
          "key_tail_pairs": 1188,
          "query_elements": 864,
          "query_tail_pairs": 1188
        },
        "unexplained_instructions_per_call": 70450.66666666667,
        "unexplained_share": 0.27502387811879464
      },
      {
        "calls": 3,
        "instructions_per_call": 177954.33333333334,
        "state": {
          "attention_pairs": 4096,
          "key_tail_pairs": 0,
          "query_elements": 1024,
          "query_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 32704.666666666664,
        "unexplained_share": 0.18378123226370807
      },
      {
        "calls": 3,
        "instructions_per_call": 247212.0,
        "state": {
          "attention_pairs": 9216,
          "key_tail_pairs": 0,
          "query_elements": 1536,
          "query_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 69323.0,
        "unexplained_share": 0.2804192353122017
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 28.04192353122017,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 28.04192353122017,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}