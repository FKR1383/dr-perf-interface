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
    "hypothesis": "Combining independent rotary elementwise work with attention remainder work may explain the residuals better than either previous model alone. For these short sequences, full vector-block attention work may be less important than these two costs.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * attn.inner_dim * (hidden_states.shape[1] + (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]))",
        "name": "projection_elements",
        "rationale": "Captures projection and normalization costs across query and context tokens."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim if rotary_emb is not None else 0",
        "name": "rotary_elements",
        "rationale": "Restores an independent linear cost for rotary operations, which the previous candidate omitted."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * ((hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]) % 16)",
        "name": "attention_tail_elements",
        "rationale": "Captures scalar attention remainder work across all query rows, including short cross-attention contexts."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Separates fixed rotary dispatch and allocation overhead from its elementwise cost."
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
        "attention_tail_elements": 40.72318175113853,
        "projection_elements": 16.67786774296019,
        "rotary_elements": 113.19428528566993,
        "uses_rotary": 321203.9059712227
      },
      "constant": 626236.3177092357,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.649506498128176,
    "max_unexplained_share": 0.1756382557316771,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "projection_elements",
      "rotary_elements",
      "attention_tail_elements",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1561196.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 682272.0,
        "state": {
          "attention_tail_elements": 144,
          "projection_elements": 416,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 46695.666666666664,
        "unexplained_share": 0.06844142316651813
      },
      {
        "calls": 3,
        "instructions_per_call": 1097559.0,
        "state": {
          "attention_tail_elements": 324,
          "projection_elements": 576,
          "rotary_elements": 288,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 75344.0,
        "unexplained_share": 0.06864687911993797
      },
      {
        "calls": 3,
        "instructions_per_call": 715464.3333333334,
        "state": {
          "attention_tail_elements": 384,
          "projection_elements": 704,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 65752.0,
        "unexplained_share": 0.09190115696426517
      },
      {
        "calls": 3,
        "instructions_per_call": 742189.3333333334,
        "state": {
          "attention_tail_elements": 648,
          "projection_elements": 864,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 79398.33333333333,
        "unexplained_share": 0.10697854276177506
      },
      {
        "calls": 3,
        "instructions_per_call": 1089982.6666666667,
        "state": {
          "attention_tail_elements": 0,
          "projection_elements": 1024,
          "rotary_elements": 512,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 70470.33333333334,
        "unexplained_share": 0.06465271007367701
      },
      {
        "calls": 3,
        "instructions_per_call": 756936.0,
        "state": {
          "attention_tail_elements": 648,
          "projection_elements": 1056,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 90027.33333333334,
        "unexplained_share": 0.1189365195119975
      },
      {
        "calls": 3,
        "instructions_per_call": 744477.6666666666,
        "state": {
          "attention_tail_elements": 512,
          "projection_elements": 1152,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 85065.33333333334,
        "unexplained_share": 0.1142617665271356
      },
      {
        "calls": 3,
        "instructions_per_call": 1126121.0,
        "state": {
          "attention_tail_elements": 144,
          "projection_elements": 1152,
          "rotary_elements": 576,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 86475.99999999999,
        "unexplained_share": 0.07679103755280292
      },
      {
        "calls": 3,
        "instructions_per_call": 1268278.3333333333,
        "state": {
          "attention_tail_elements": 1188,
          "projection_elements": 1728,
          "rotary_elements": 864,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 145438.66666666663,
        "unexplained_share": 0.11467409230623665
      },
      {
        "calls": 3,
        "instructions_per_call": 881882.6666666666,
        "state": {
          "attention_tail_elements": 1728,
          "projection_elements": 1824,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 154892.33333333334,
        "unexplained_share": 0.1756382557316771
      },
      {
        "calls": 3,
        "instructions_per_call": 1207701.3333333333,
        "state": {
          "attention_tail_elements": 0,
          "projection_elements": 2048,
          "rotary_elements": 1024,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 113017.66666666667,
        "unexplained_share": 0.09358080805850454
      },
      {
        "calls": 3,
        "instructions_per_call": 1349137.3333333333,
        "state": {
          "attention_tail_elements": 0,
          "projection_elements": 3072,
          "rotary_elements": 1536,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 170654.0,
        "unexplained_share": 0.12649119980866785
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.56382557316771,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.56382557316771,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}