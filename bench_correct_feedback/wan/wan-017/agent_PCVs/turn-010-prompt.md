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
    "hypothesis": "Neither full attention pairs nor scalar tails sufficiently explain the largest cross-attention residual. Counting eight-element context tiles tests whether blocked kernel work, particularly the additional tile at context length 9, accounts for it.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim",
        "name": "query_elements",
        "rationale": "Captures query projection, output projection, and per-row attention work."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * (((hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]) + 7) // 8)",
        "name": "attention_context_tiles",
        "rationale": "Tests attention work measured in eight-element context tiles, including partially filled tiles."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim if rotary_emb is not None else 0",
        "name": "rotary_elements",
        "rationale": "Captures token-dependent rotary work."
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
        "attention_context_tiles": 77.78634559366108,
        "query_elements": 28.846158830201524,
        "rotary_elements": 74.05060177729158,
        "uses_rotary": 336386.0187793083
      },
      "constant": 639389.9864971389,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.635215217713267,
    "max_unexplained_share": 0.20478540900792663,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "attention_context_tiles",
      "rotary_elements",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1563152.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 681374.0,
        "state": {
          "attention_context_tiles": 36,
          "query_elements": 288,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 35901.666666666664,
        "unexplained_share": 0.05269010362395199
      },
      {
        "calls": 3,
        "instructions_per_call": 1099576.0,
        "state": {
          "attention_context_tiles": 72,
          "query_elements": 288,
          "rotary_elements": 288,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 67604.0,
        "unexplained_share": 0.061481880288402076
      },
      {
        "calls": 3,
        "instructions_per_call": 713656.3333333334,
        "state": {
          "attention_context_tiles": 64,
          "query_elements": 512,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 59251.666666666664,
        "unexplained_share": 0.08302548985996527
      },
      {
        "calls": 3,
        "instructions_per_call": 1087005.3333333333,
        "state": {
          "attention_context_tiles": 128,
          "query_elements": 512,
          "rotary_elements": 512,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 45383.99999999999,
        "unexplained_share": 0.041751405083569046
      },
      {
        "calls": 3,
        "instructions_per_call": 741639.3333333334,
        "state": {
          "attention_context_tiles": 144,
          "query_elements": 576,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 83021.66666666666,
        "unexplained_share": 0.11194345139910772
      },
      {
        "calls": 3,
        "instructions_per_call": 1123827.0,
        "state": {
          "attention_context_tiles": 216,
          "query_elements": 576,
          "rotary_elements": 576,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 66940.0,
        "unexplained_share": 0.05956432796151009
      },
      {
        "calls": 3,
        "instructions_per_call": 754685.3333333334,
        "state": {
          "attention_context_tiles": 108,
          "query_elements": 864,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 86906.00000000001,
        "unexplained_share": 0.1151552788446929
      },
      {
        "calls": 3,
        "instructions_per_call": 1267761.6666666667,
        "state": {
          "attention_context_tiles": 432,
          "query_elements": 864,
          "rotary_elements": 864,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 162474.99999999997,
        "unexplained_share": 0.12815894680519602
      },
      {
        "calls": 3,
        "instructions_per_call": 745294.0,
        "state": {
          "attention_context_tiles": 128,
          "query_elements": 1024,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 74878.00000000001,
        "unexplained_share": 0.1004677348804633
      },
      {
        "calls": 3,
        "instructions_per_call": 1207045.6666666667,
        "state": {
          "attention_context_tiles": 512,
          "query_elements": 1024,
          "rotary_elements": 1024,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 80074.66666666667,
        "unexplained_share": 0.06633938456346722
      },
      {
        "calls": 3,
        "instructions_per_call": 881164.6666666666,
        "state": {
          "attention_context_tiles": 384,
          "query_elements": 1536,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 180449.66666666666,
        "unexplained_share": 0.20478540900792663
      },
      {
        "calls": 3,
        "instructions_per_call": 1349469.0,
        "state": {
          "attention_context_tiles": 1152,
          "query_elements": 1536,
          "rotary_elements": 1536,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 123643.33333333334,
        "unexplained_share": 0.09162369297355726
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 20.478540900792662,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 20.478540900792662,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}