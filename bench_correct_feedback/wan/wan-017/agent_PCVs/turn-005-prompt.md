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
    "hypothesis": "Attention remainder work scales with query rows times the context-length remainder. Splitting vector blocks from scalar tails should better explain both short cross-attention contexts and the elevated self-attention count at length 27.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] + (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]))",
        "name": "projection_tokens",
        "rationale": "Captures projection and normalization work over query and context tokens."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * ((hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]) // 16)",
        "name": "attention_vector_blocks",
        "rationale": "Measures complete 16-element context blocks processed across attention rows."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * ((hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]) % 16)",
        "name": "attention_scalar_tail",
        "rationale": "Measures remainder elements across every attention row, including short cross-attention contexts; scalar remainder costs can differ substantially from vectorized blocks."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Captures fixed overhead from the rotary embedding path."
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
        "attention_scalar_tail": 41.588734427694156,
        "attention_vector_blocks": 55.62623148168471,
        "projection_tokens": -29.442564928650373,
        "uses_rotary": 324473.4233260007
      },
      "constant": 643231.9760329264,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.64068241789937,
    "max_unexplained_share": 0.2552090535404941,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "projection_tokens",
      "attention_vector_blocks",
      "attention_scalar_tail",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1560620.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 682045.0,
        "state": {
          "attention_scalar_tail": 144,
          "attention_vector_blocks": 0,
          "projection_tokens": 13,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 43404.333333333336,
        "unexplained_share": 0.06363851847507618
      },
      {
        "calls": 3,
        "instructions_per_call": 1101553.6666666667,
        "state": {
          "attention_scalar_tail": 324,
          "attention_vector_blocks": 0,
          "projection_tokens": 18,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 104255.66666666666,
        "unexplained_share": 0.09464420102394767
      },
      {
        "calls": 3,
        "instructions_per_call": 714865.6666666666,
        "state": {
          "attention_scalar_tail": 384,
          "attention_vector_blocks": 0,
          "projection_tokens": 22,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 62640.33333333333,
        "unexplained_share": 0.08762532074790741
      },
      {
        "calls": 3,
        "instructions_per_call": 741199.6666666666,
        "state": {
          "attention_scalar_tail": 648,
          "attention_vector_blocks": 0,
          "projection_tokens": 27,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 77201.0,
        "unexplained_share": 0.10415681964239057
      },
      {
        "calls": 3,
        "instructions_per_call": 1087517.0,
        "state": {
          "attention_scalar_tail": 0,
          "attention_vector_blocks": 64,
          "projection_tokens": 32,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 121667.33333333334,
        "unexplained_share": 0.11187625879258287
      },
      {
        "calls": 3,
        "instructions_per_call": 754823.6666666666,
        "state": {
          "attention_scalar_tail": 648,
          "attention_vector_blocks": 0,
          "projection_tokens": 33,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 87477.66666666667,
        "unexplained_share": 0.11589152610035634
      },
      {
        "calls": 3,
        "instructions_per_call": 743221.6666666666,
        "state": {
          "attention_scalar_tail": 512,
          "attention_vector_blocks": 0,
          "projection_tokens": 36,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 83737.00000000001,
        "unexplained_share": 0.1126675980472403
      },
      {
        "calls": 3,
        "instructions_per_call": 1124382.0,
        "state": {
          "attention_scalar_tail": 144,
          "attention_vector_blocks": 72,
          "projection_tokens": 36,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 146499.00000000003,
        "unexplained_share": 0.13029290757055878
      },
      {
        "calls": 3,
        "instructions_per_call": 1265655.6666666667,
        "state": {
          "attention_scalar_tail": 1188,
          "attention_vector_blocks": 108,
          "projection_tokens": 54,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 242863.0,
        "unexplained_share": 0.19188710357503763
      },
      {
        "calls": 3,
        "instructions_per_call": 880655.6666666666,
        "state": {
          "attention_scalar_tail": 1728,
          "attention_vector_blocks": 0,
          "projection_tokens": 57,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 158542.99999999997,
        "unexplained_share": 0.18002836522939156
      },
      {
        "calls": 3,
        "instructions_per_call": 1204949.6666666667,
        "state": {
          "attention_scalar_tail": 0,
          "attention_vector_blocks": 256,
          "projection_tokens": 64,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 227196.33333333334,
        "unexplained_share": 0.18855255088110182
      },
      {
        "calls": 3,
        "instructions_per_call": 1347509.6666666667,
        "state": {
          "attention_scalar_tail": 0,
          "attention_vector_blocks": 576,
          "projection_tokens": 96,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 343896.66666666674,
        "unexplained_share": 0.2552090535404941
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 25.52090535404941,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 25.52090535404941,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}