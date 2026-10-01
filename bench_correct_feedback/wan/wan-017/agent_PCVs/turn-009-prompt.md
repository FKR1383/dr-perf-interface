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
    "hypothesis": "Keeping direct query scaling while replacing remainder counts with complete attention-pair counts may explain additional matrix-multiplication work, particularly at length 48. This differs from iteration 1 by exposing query size independently of context size.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim",
        "name": "query_elements",
        "rationale": "Retains direct query-row scaling, which improved the previous result."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])",
        "name": "attention_pairs",
        "rationale": "Captures the complete attention matrix, including work on full context blocks omitted by the remainder-only feature."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim if rotary_emb is not None else 0",
        "name": "rotary_elements",
        "rationale": "Captures token-dependent rotary work separately from shared query processing."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Captures fixed rotary overhead."
      }
    ]
  },
  "case_id": "wan-017",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-017",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "attention_pairs": 10.300969497200438,
        "query_elements": 33.44178343435888,
        "rotary_elements": 55.733198078125824,
        "uses_rotary": 345198.02703521657
      },
      "constant": 642321.9441380039,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.64157131128013,
    "max_unexplained_share": 0.20418227350557305,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "attention_pairs",
      "rotary_elements",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1562743.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 681892.3333333334,
        "state": {
          "attention_pairs": 144,
          "query_elements": 288,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 35842.333333333336,
        "unexplained_share": 0.05256303903304383
      },
      {
        "calls": 3,
        "instructions_per_call": 1099984.0,
        "state": {
          "attention_pairs": 324,
          "query_elements": 288,
          "rotary_elements": 288,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 65481.0,
        "unexplained_share": 0.0595290476952392
      },
      {
        "calls": 3,
        "instructions_per_call": 713745.3333333334,
        "state": {
          "attention_pairs": 384,
          "query_elements": 512,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 58554.0,
        "unexplained_share": 0.08203766422757697
      },
      {
        "calls": 3,
        "instructions_per_call": 1087089.0,
        "state": {
          "attention_pairs": 1024,
          "query_elements": 512,
          "rotary_elements": 512,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 43450.0,
        "unexplained_share": 0.03996912856261079
      },
      {
        "calls": 3,
        "instructions_per_call": 741959.6666666666,
        "state": {
          "attention_pairs": 648,
          "query_elements": 576,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 82617.99999999999,
        "unexplained_share": 0.11135106625292748
      },
      {
        "calls": 3,
        "instructions_per_call": 1124178.0,
        "state": {
          "attention_pairs": 1296,
          "query_elements": 576,
          "rotary_elements": 576,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 65176.66666666667,
        "unexplained_share": 0.057977176805333916
      },
      {
        "calls": 3,
        "instructions_per_call": 754963.3333333334,
        "state": {
          "attention_pairs": 648,
          "query_elements": 864,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 86282.33333333333,
        "unexplained_share": 0.11428678655475541
      },
      {
        "calls": 3,
        "instructions_per_call": 1268044.6666666667,
        "state": {
          "attention_pairs": 2916,
          "query_elements": 864,
          "rotary_elements": 864,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 160521.3333333333,
        "unexplained_share": 0.12658965220468046
      },
      {
        "calls": 3,
        "instructions_per_call": 745594.3333333334,
        "state": {
          "attention_pairs": 512,
          "query_elements": 1024,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 74170.0,
        "unexplained_share": 0.09947768737512758
      },
      {
        "calls": 3,
        "instructions_per_call": 1207371.3333333333,
        "state": {
          "attention_pairs": 4096,
          "query_elements": 1024,
          "rotary_elements": 1024,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 77877.66666666666,
        "unexplained_share": 0.064501835116178
      },
      {
        "calls": 3,
        "instructions_per_call": 881291.0,
        "state": {
          "attention_pairs": 1728,
          "query_elements": 1536,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 179943.99999999997,
        "unexplained_share": 0.20418227350557305
      },
      {
        "calls": 3,
        "instructions_per_call": 1349595.3333333333,
        "state": {
          "attention_pairs": 9216,
          "query_elements": 1536,
          "rotary_elements": 1536,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 121916.00000000001,
        "unexplained_share": 0.09033522641107732
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 20.418227350557306,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 20.418227350557306,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}