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
    "hypothesis": "Instruction counts combine fixed overhead, token-linear projection and normalization costs, attention-pair costs, and fixed plus elementwise rotary costs.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] + (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])) * attn.inner_dim",
        "name": "projection_elements",
        "rationale": "Captures linear projection and normalization work across query and context tokens; model widths are fixed."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])",
        "name": "attention_pairs",
        "rationale": "Captures attention matrix multiplication and softmax work."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim if rotary_emb is not None else 0",
        "name": "rotary_elements",
        "rationale": "Captures elementwise rotary embedding work on the self-attention path."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Captures fixed dispatch, slicing, allocation, and operator overhead from applying rotary embeddings."
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
        "attention_pairs": 10.067690336990728,
        "projection_elements": 11.123644727386896,
        "rotary_elements": 53.22970150160999,
        "uses_rotary": 342630.83358141955
      },
      "constant": 639624.4485837473,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.639291769824922,
    "max_unexplained_share": 0.24262399876684115,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "projection_elements",
      "attention_pairs",
      "rotary_elements",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1559129.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 682596.3333333334,
        "state": {
          "attention_pairs": 144,
          "projection_elements": 416,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 43491.00000000001,
        "unexplained_share": 0.06371408382406586
      },
      {
        "calls": 3,
        "instructions_per_call": 1101066.3333333333,
        "state": {
          "attention_pairs": 324,
          "projection_elements": 576,
          "rotary_elements": 288,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 74064.66666666667,
        "unexplained_share": 0.06726630760060173
      },
      {
        "calls": 3,
        "instructions_per_call": 715477.3333333334,
        "state": {
          "attention_pairs": 384,
          "projection_elements": 704,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 71255.00000000001,
        "unexplained_share": 0.0995908558948059
      },
      {
        "calls": 3,
        "instructions_per_call": 741330.6666666666,
        "state": {
          "attention_pairs": 648,
          "projection_elements": 864,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 95730.66666666666,
        "unexplained_share": 0.12913355803438142
      },
      {
        "calls": 3,
        "instructions_per_call": 1088494.6666666667,
        "state": {
          "attention_pairs": 1024,
          "projection_elements": 1024,
          "rotary_elements": 512,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 56501.99999999999,
        "unexplained_share": 0.05190838479073851
      },
      {
        "calls": 3,
        "instructions_per_call": 756324.6666666666,
        "state": {
          "attention_pairs": 648,
          "projection_elements": 1056,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 106088.0,
        "unexplained_share": 0.14026780386200988
      },
      {
        "calls": 3,
        "instructions_per_call": 745214.3333333334,
        "state": {
          "attention_pairs": 512,
          "projection_elements": 1152,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 96775.33333333333,
        "unexplained_share": 0.1298624154214246
      },
      {
        "calls": 3,
        "instructions_per_call": 1125682.3333333333,
        "state": {
          "attention_pairs": 1296,
          "projection_elements": 1152,
          "rotary_elements": 576,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 79294.33333333333,
        "unexplained_share": 0.07044112800325254
      },
      {
        "calls": 3,
        "instructions_per_call": 1268654.6666666667,
        "state": {
          "attention_pairs": 2916,
          "projection_elements": 1728,
          "rotary_elements": 864,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 180524.99999999997,
        "unexplained_share": 0.1422964063769389
      },
      {
        "calls": 3,
        "instructions_per_call": 882287.0,
        "state": {
          "attention_pairs": 1728,
          "projection_elements": 1824,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 214063.99999999997,
        "unexplained_share": 0.24262399876684115
      },
      {
        "calls": 3,
        "instructions_per_call": 1207454.6666666667,
        "state": {
          "attention_pairs": 4096,
          "projection_elements": 2048,
          "rotary_elements": 1024,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 99875.0,
        "unexplained_share": 0.0827153207132138
      },
      {
        "calls": 3,
        "instructions_per_call": 1348894.6666666667,
        "state": {
          "attention_pairs": 9216,
          "projection_elements": 3072,
          "rotary_elements": 1536,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 154412.33333333334,
        "unexplained_share": 0.11447323289883767
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 24.262399876684114,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 24.262399876684114,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}