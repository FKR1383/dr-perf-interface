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

This is iteration 3. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The observed self-attention counts suggest a linear length cost plus a remainder penalty at nonmultiples of 16. Separate query and context slopes should also improve cross-attention predictions.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1]",
        "name": "query_tokens",
        "rationale": "Captures query projection, output projection, and attention work that grows with query length."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])",
        "name": "context_tokens",
        "rationale": "Allows context projection and normalization costs to have a separate fitted slope."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Captures the substantial fixed overhead separating self-attention with rotary embeddings from cross-attention."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] % 16) if rotary_emb is not None else 0",
        "name": "rotary_tail",
        "rationale": "Tests whether vectorized kernel remainder handling explains elevated self-attention costs at lengths 9, 18, and 27 relative to multiples of 16."
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
        "context_tokens": 382.08409666010755,
        "query_tokens": 1221.3727392913306,
        "rotary_tail": 65.86576191417583,
        "uses_rotary": 321042.27785497427
      },
      "constant": 630887.9711790428,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.62547471933067,
    "max_unexplained_share": 0.2317231500963918,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_tokens",
      "context_tokens",
      "uses_rotary",
      "rotary_tail"
    ],
    "raw_files": [
      "run.1559633.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 681828.6666666666,
        "state": {
          "context_tokens": 4,
          "query_tokens": 9,
          "rotary_tail": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 44070.666666666664,
        "unexplained_share": 0.06463598381998215
      },
      {
        "calls": 3,
        "instructions_per_call": 1096733.3333333333,
        "state": {
          "context_tokens": 9,
          "query_tokens": 9,
          "rotary_tail": 9,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 110375.0,
        "unexplained_share": 0.10063977873685491
      },
      {
        "calls": 3,
        "instructions_per_call": 714423.6666666666,
        "state": {
          "context_tokens": 6,
          "query_tokens": 16,
          "rotary_tail": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 66828.0,
        "unexplained_share": 0.09354113408896962
      },
      {
        "calls": 3,
        "instructions_per_call": 1088161.3333333333,
        "state": {
          "context_tokens": 16,
          "query_tokens": 16,
          "rotary_tail": 0,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 113862.0,
        "unexplained_share": 0.10463705749515084
      },
      {
        "calls": 3,
        "instructions_per_call": 742678.6666666666,
        "state": {
          "context_tokens": 9,
          "query_tokens": 18,
          "rotary_tail": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 90155.33333333333,
        "unexplained_share": 0.12139211395148014
      },
      {
        "calls": 3,
        "instructions_per_call": 1123572.3333333333,
        "state": {
          "context_tokens": 18,
          "query_tokens": 18,
          "rotary_tail": 2,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 141068.33333333334,
        "unexplained_share": 0.12555340599640968
      },
      {
        "calls": 3,
        "instructions_per_call": 754432.6666666666,
        "state": {
          "context_tokens": 6,
          "query_tokens": 27,
          "rotary_tail": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 93229.66666666669,
        "unexplained_share": 0.12357586141992795
      },
      {
        "calls": 3,
        "instructions_per_call": 1268056.3333333333,
        "state": {
          "context_tokens": 27,
          "query_tokens": 27,
          "rotary_tail": 11,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 270277.00000000006,
        "unexplained_share": 0.2131427389266881
      },
      {
        "calls": 3,
        "instructions_per_call": 745027.3333333334,
        "state": {
          "context_tokens": 4,
          "query_tokens": 32,
          "rotary_tail": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 80499.66666666667,
        "unexplained_share": 0.10804927962374535
      },
      {
        "calls": 3,
        "instructions_per_call": 1205699.6666666667,
        "state": {
          "context_tokens": 32,
          "query_tokens": 32,
          "rotary_tail": 0,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 205042.0,
        "unexplained_share": 0.1700605927567921
      },
      {
        "calls": 3,
        "instructions_per_call": 880883.6666666666,
        "state": {
          "context_tokens": 9,
          "query_tokens": 48,
          "rotary_tail": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 186830.0,
        "unexplained_share": 0.21209384061686543
      },
      {
        "calls": 3,
        "instructions_per_call": 1350219.0,
        "state": {
          "context_tokens": 48,
          "query_tokens": 48,
          "rotary_tail": 0,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 312877.00000000006,
        "unexplained_share": 0.2317231500963918
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 23.17231500963918,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 23.17231500963918,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}