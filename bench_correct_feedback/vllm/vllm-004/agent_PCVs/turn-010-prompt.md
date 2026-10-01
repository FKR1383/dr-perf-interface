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
    "hypothesis": "Layer identity did not explain the persistent discrepancy. Rounded query tiles and causal tile traversal may capture native loop counts more accurately than unrounded token-context products.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens",
        "name": "query_tokens",
        "rationale": "Captures processing proportional to actual query rows."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel() * ((attn_metadata.max_query_len + 15) // 16)",
        "name": "query_tiles",
        "rationale": "Models query work rounded to 16-row tiles."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel() * (((attn_metadata.max_query_len + 15) // 16 + 1) ** 2 // 4 if attn_metadata.causal and attn_metadata.max_query_len == attn_metadata.max_seq_len else (attn_metadata.max_query_len + 15) // 16 * ((attn_metadata.max_seq_len + 31) // 32))",
        "name": "causal_attention_tiles",
        "rationale": "Approximates triangular tile traversal for full causal prefill and rectangular traversal for cached queries."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel()",
        "name": "requests",
        "rationale": "Separates per-request setup from tiled kernel work."
      }
    ]
  },
  "case_id": "vllm-004",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 336,
    "case": "vllm-004",
    "distinct_states": 17,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "causal_attention_tiles": 256.4425436061774,
        "query_tiles": -3223.82918472466,
        "query_tokens": 3826.906712865884,
        "requests": 2184.2302738886947
      },
      "constant": 99898.50601205757,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 102.17815975891426,
    "max_unexplained_share": 0.7931735444742917,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_tokens",
      "query_tiles",
      "causal_attention_tiles",
      "requests"
    ],
    "raw_files": [
      "run.1798394.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 36,
        "instructions_per_call": 123270.19444444444,
        "state": {
          "causal_attention_tiles": 1,
          "query_tiles": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 27728.58333333334,
        "unexplained_share": 0.22494150721754633
      },
      {
        "calls": 24,
        "instructions_per_call": 138651.5,
        "state": {
          "causal_attention_tiles": 2,
          "query_tiles": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 42838.29166666666,
        "unexplained_share": 0.3089637808943045
      },
      {
        "calls": 48,
        "instructions_per_call": 152202.02083333334,
        "state": {
          "causal_attention_tiles": 2,
          "query_tiles": 2,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 51255.520833333336,
        "unexplained_share": 0.33675979170775905
      },
      {
        "calls": 36,
        "instructions_per_call": 183076.61111111112,
        "state": {
          "causal_attention_tiles": 4,
          "query_tiles": 2,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 81817.13888888888,
        "unexplained_share": 0.4469010999948715
      },
      {
        "calls": 12,
        "instructions_per_call": 180483.41666666666,
        "state": {
          "causal_attention_tiles": 3,
          "query_tiles": 3,
          "query_tokens": 3,
          "requests": 3
        },
        "unexplained_instructions_per_call": 74835.58333333331,
        "unexplained_share": 0.41463966449364453
      },
      {
        "calls": 24,
        "instructions_per_call": 227546.33333333334,
        "state": {
          "causal_attention_tiles": 6,
          "query_tiles": 3,
          "query_tokens": 3,
          "requests": 3
        },
        "unexplained_instructions_per_call": 121049.54166666669,
        "unexplained_share": 0.5319775532895132
      },
      {
        "calls": 24,
        "instructions_per_call": 271503.6666666667,
        "state": {
          "causal_attention_tiles": 8,
          "query_tiles": 4,
          "query_tokens": 4,
          "requests": 4
        },
        "unexplained_instructions_per_call": 159914.58333333337,
        "unexplained_share": 0.5889960356582048
      },
      {
        "calls": 24,
        "instructions_per_call": 315210.375,
        "state": {
          "causal_attention_tiles": 10,
          "query_tiles": 5,
          "query_tokens": 5,
          "requests": 5
        },
        "unexplained_instructions_per_call": 198285.375,
        "unexplained_share": 0.6290572605676447
      },
      {
        "calls": 12,
        "instructions_per_call": 358770.0,
        "state": {
          "causal_attention_tiles": 12,
          "query_tiles": 6,
          "query_tokens": 6,
          "requests": 6
        },
        "unexplained_instructions_per_call": 236849.66666666663,
        "unexplained_share": 0.6601713261049325
      },
      {
        "calls": 12,
        "instructions_per_call": 280767.5,
        "state": {
          "causal_attention_tiles": 1,
          "query_tiles": 1,
          "query_tokens": 10,
          "requests": 1
        },
        "unexplained_instructions_per_call": 135113.25,
        "unexplained_share": 0.48122824044805756
      },
      {
        "calls": 12,
        "instructions_per_call": 446314.5833333333,
        "state": {
          "causal_attention_tiles": 2,
          "query_tiles": 2,
          "query_tokens": 20,
          "requests": 2
        },
        "unexplained_instructions_per_call": 278399.25,
        "unexplained_share": 0.6237735901900285
      },
      {
        "calls": 12,
        "instructions_per_call": 1149107.5833333333,
        "state": {
          "causal_attention_tiles": 6,
          "query_tiles": 6,
          "query_tokens": 66,
          "requests": 3
        },
        "unexplained_instructions_per_call": 809167.7499999999,
        "unexplained_share": 0.7041705770079114
      },
      {
        "calls": 12,
        "instructions_per_call": 1478155.0833333333,
        "state": {
          "causal_attention_tiles": 8,
          "query_tiles": 8,
          "query_tokens": 84,
          "requests": 4
        },
        "unexplained_instructions_per_call": 1070851.916666667,
        "unexplained_share": 0.7244516686651228
      },
      {
        "calls": 12,
        "instructions_per_call": 4391275.916666667,
        "state": {
          "causal_attention_tiles": 20,
          "query_tiles": 15,
          "query_tokens": 230,
          "requests": 5
        },
        "unexplained_instructions_per_call": 3439763.0833333326,
        "unexplained_share": 0.7833174568416531
      },
      {
        "calls": 12,
        "instructions_per_call": 5213207.666666667,
        "state": {
          "causal_attention_tiles": 24,
          "query_tiles": 18,
          "query_tokens": 270,
          "requests": 6
        },
        "unexplained_instructions_per_call": 4111736.000000001,
        "unexplained_share": 0.7887151755512266
      },
      {
        "calls": 12,
        "instructions_per_call": 6103991.25,
        "state": {
          "causal_attention_tiles": 28,
          "query_tiles": 21,
          "query_tokens": 322,
          "requests": 7
        },
        "unexplained_instructions_per_call": 4808728.666666666,
        "unexplained_share": 0.7878007142730858
      },
      {
        "calls": 12,
        "instructions_per_call": 7092428.833333333,
        "state": {
          "causal_attention_tiles": 32,
          "query_tiles": 24,
          "query_tokens": 368,
          "requests": 8
        },
        "unexplained_instructions_per_call": 5625526.916666665,
        "unexplained_share": 0.7931735444742917
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 79.31735444742917,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 79.31735444742917,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}