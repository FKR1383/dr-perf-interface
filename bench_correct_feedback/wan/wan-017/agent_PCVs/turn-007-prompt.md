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

This is iteration 7. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Combining query and context sizes may leave their independently scaling operations unexplained. Separate query, context, and rotary element counts should capture these costs, while the fixed rotary indicator accounts for branch overhead.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim",
        "name": "query_elements",
        "rationale": "Separately exposes query and output projection work, rather than combining it with context length."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]) * attn.inner_dim",
        "name": "context_elements",
        "rationale": "Separately exposes key/value projection and key normalization work."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim if rotary_emb is not None else 0",
        "name": "rotary_elements",
        "rationale": "Captures the additional token-dependent work specific to rotary self-attention."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Captures fixed rotary operator overhead independently of sequence length."
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
        "context_elements": 24.91099621212102,
        "query_elements": 36.425802685950394,
        "rotary_elements": 102.33986845730159,
        "uses_rotary": 321500.41034710733
      },
      "constant": 630542.9925270859,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.6609797347337,
    "max_unexplained_share": 0.21349485944352578,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "context_elements",
      "rotary_elements",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1561636.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 682238.0,
        "state": {
          "context_elements": 128,
          "query_elements": 288,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 43820.0,
        "unexplained_share": 0.0642297849137691
      },
      {
        "calls": 3,
        "instructions_per_call": 1097151.3333333333,
        "state": {
          "context_elements": 288,
          "query_elements": 288,
          "rotary_elements": 288,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 78322.66666666666,
        "unexplained_share": 0.07138729570578838
      },
      {
        "calls": 3,
        "instructions_per_call": 713563.0,
        "state": {
          "context_elements": 192,
          "query_elements": 512,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 66461.66666666666,
        "unexplained_share": 0.09314057296505937
      },
      {
        "calls": 3,
        "instructions_per_call": 1086754.3333333333,
        "state": {
          "context_elements": 512,
          "query_elements": 512,
          "rotary_elements": 512,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 53646.666666666664,
        "unexplained_share": 0.04936411571704492
      },
      {
        "calls": 3,
        "instructions_per_call": 742163.6666666666,
        "state": {
          "context_elements": 288,
          "query_elements": 576,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 90149.33333333333,
        "unexplained_share": 0.12146826553531993
      },
      {
        "calls": 3,
        "instructions_per_call": 1123198.0,
        "state": {
          "context_elements": 576,
          "query_elements": 576,
          "rotary_elements": 576,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 73967.0,
        "unexplained_share": 0.065853927802578
      },
      {
        "calls": 3,
        "instructions_per_call": 755217.0,
        "state": {
          "context_elements": 192,
          "query_elements": 864,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 93807.33333333334,
        "unexplained_share": 0.12421242283123042
      },
      {
        "calls": 3,
        "instructions_per_call": 1264320.6666666667,
        "state": {
          "context_elements": 864,
          "query_elements": 864,
          "rotary_elements": 864,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 168851.0,
        "unexplained_share": 0.13355077113875646
      },
      {
        "calls": 3,
        "instructions_per_call": 745484.3333333334,
        "state": {
          "context_elements": 128,
          "query_elements": 1024,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 81122.66666666667,
        "unexplained_share": 0.10881874110477618
      },
      {
        "calls": 3,
        "instructions_per_call": 1204316.3333333333,
        "state": {
          "context_elements": 1024,
          "query_elements": 1024,
          "rotary_elements": 1024,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 85325.0,
        "unexplained_share": 0.07084932557863396
      },
      {
        "calls": 3,
        "instructions_per_call": 880903.3333333334,
        "state": {
          "context_elements": 288,
          "query_elements": 1536,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 188068.33333333334,
        "unexplained_share": 0.21349485944352578
      },
      {
        "calls": 3,
        "instructions_per_call": 1347070.6666666667,
        "state": {
          "context_elements": 1536,
          "query_elements": 1536,
          "rotary_elements": 1536,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 132537.0,
        "unexplained_share": 0.098389047642143
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 21.34948594435258,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 21.34948594435258,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}