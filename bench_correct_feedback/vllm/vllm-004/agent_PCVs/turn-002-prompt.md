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
    "hypothesis": "Instruction count combines fixed wrapper overhead, per-request setup, token processing, and attention arithmetic with block rounding.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens * self.num_heads * self.head_size",
        "name": "query_elements",
        "rationale": "Captures query and output processing proportional to actual token count."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens * attn_metadata.max_seq_len * self.num_heads * self.head_size",
        "name": "attention_work",
        "rationale": "Approximates query-key and attention-value arithmetic using constant-time entry metadata."
      },
      {
        "expression": "0 if attn_metadata is None else (attn_metadata.query_start_loc.numel() - 1) * ((attn_metadata.max_query_len + 31) // 32) * ((attn_metadata.max_seq_len + 31) // 32) * self.num_heads",
        "name": "attention_tiles",
        "rationale": "Captures block-rounded attention work and differences between prefill and decode."
      },
      {
        "expression": "0 if attn_metadata is None else (attn_metadata.query_start_loc.numel() - 1) * self.num_heads",
        "name": "request_heads",
        "rationale": "Captures per-request, per-head setup and scheduling overhead; warm-up calls yield zero."
      }
    ]
  },
  "case_id": "vllm-004",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 336,
    "case": "vllm-004",
    "distinct_states": 25,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "attention_tiles": 22.141047881754453,
        "attention_work": -0.000999560647692606,
        "query_elements": 5.045034896359019,
        "request_heads": 162.49429921340194
      },
      "constant": 91415.3229785413,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 128.76972533389926,
    "max_unexplained_share": 0.7841777549394127,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "attention_work",
      "attention_tiles",
      "request_heads"
    ],
    "raw_files": [
      "run.1792277.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 12,
        "instructions_per_call": 124028.58333333333,
        "state": {
          "attention_tiles": 12,
          "attention_work": 9984,
          "query_elements": 768,
          "request_heads": 12
        },
        "unexplained_instructions_per_call": 27449.0,
        "unexplained_share": 0.22131188845581967
      },
      {
        "calls": 12,
        "instructions_per_call": 123024.16666666667,
        "state": {
          "attention_tiles": 12,
          "attention_work": 18432,
          "query_elements": 768,
          "request_heads": 12
        },
        "unexplained_instructions_per_call": 26801.75,
        "unexplained_share": 0.21785760250357314
      },
      {
        "calls": 12,
        "instructions_per_call": 122877.41666666667,
        "state": {
          "attention_tiles": 12,
          "attention_work": 19200,
          "query_elements": 768,
          "request_heads": 12
        },
        "unexplained_instructions_per_call": 26750.583333333332,
        "unexplained_share": 0.21770138125462435
      },
      {
        "calls": 12,
        "instructions_per_call": 138433.83333333334,
        "state": {
          "attention_tiles": 24,
          "attention_work": 36864,
          "query_elements": 768,
          "request_heads": 12
        },
        "unexplained_instructions_per_call": 42158.916666666664,
        "unexplained_share": 0.3045420014134309
      },
      {
        "calls": 12,
        "instructions_per_call": 138872.0,
        "state": {
          "attention_tiles": 24,
          "attention_work": 37632,
          "query_elements": 768,
          "request_heads": 12
        },
        "unexplained_instructions_per_call": 42193.416666666664,
        "unexplained_share": 0.3038295456727538
      },
      {
        "calls": 12,
        "instructions_per_call": 153331.58333333334,
        "state": {
          "attention_tiles": 24,
          "attention_work": 18432,
          "query_elements": 1536,
          "request_heads": 24
        },
        "unexplained_instructions_per_call": 50319.333333333336,
        "unexplained_share": 0.3281733106736544
      },
      {
        "calls": 24,
        "instructions_per_call": 151940.08333333334,
        "state": {
          "attention_tiles": 24,
          "attention_work": 35328,
          "query_elements": 1536,
          "request_heads": 24
        },
        "unexplained_instructions_per_call": 49096.375,
        "unexplained_share": 0.32312984120385174
      },
      {
        "calls": 12,
        "instructions_per_call": 151841.83333333334,
        "state": {
          "attention_tiles": 24,
          "attention_work": 36864,
          "query_elements": 1536,
          "request_heads": 24
        },
        "unexplained_instructions_per_call": 48996.083333333336,
        "unexplained_share": 0.32267842305205746
      },
      {
        "calls": 24,
        "instructions_per_call": 183314.75,
        "state": {
          "attention_tiles": 48,
          "attention_work": 73728,
          "query_elements": 1536,
          "request_heads": 24
        },
        "unexplained_instructions_per_call": 80225.0,
        "unexplained_share": 0.4376352693932158
      },
      {
        "calls": 12,
        "instructions_per_call": 182962.0,
        "state": {
          "attention_tiles": 48,
          "attention_work": 75264,
          "query_elements": 1536,
          "request_heads": 24
        },
        "unexplained_instructions_per_call": 80072.5,
        "unexplained_share": 0.4376455220209661
      },
      {
        "calls": 12,
        "instructions_per_call": 180516.91666666666,
        "state": {
          "attention_tiles": 36,
          "attention_work": 50688,
          "query_elements": 2304,
          "request_heads": 36
        },
        "unexplained_instructions_per_call": 71834.33333333333,
        "unexplained_share": 0.3979368507937622
      },
      {
        "calls": 24,
        "instructions_per_call": 227475.0,
        "state": {
          "attention_tiles": 72,
          "attention_work": 108288,
          "query_elements": 2304,
          "request_heads": 36
        },
        "unexplained_instructions_per_call": 118333.29166666667,
        "unexplained_share": 0.5202035022163608
      },
      {
        "calls": 12,
        "instructions_per_call": 271776.0833333333,
        "state": {
          "attention_tiles": 96,
          "attention_work": 147456,
          "query_elements": 3072,
          "request_heads": 48
        },
        "unexplained_instructions_per_call": 156219.91666666666,
        "unexplained_share": 0.5748111266842526
      },
      {
        "calls": 12,
        "instructions_per_call": 271669.3333333333,
        "state": {
          "attention_tiles": 96,
          "attention_work": 150528,
          "query_elements": 3072,
          "request_heads": 48
        },
        "unexplained_instructions_per_call": 156184.91666666666,
        "unexplained_share": 0.5749081604106954
      },
      {
        "calls": 12,
        "instructions_per_call": 314954.75,
        "state": {
          "attention_tiles": 120,
          "attention_work": 176640,
          "query_elements": 3840,
          "request_heads": 60
        },
        "unexplained_instructions_per_call": 193585.33333333334,
        "unexplained_share": 0.6146449079854593
      },
      {
        "calls": 12,
        "instructions_per_call": 315199.5,
        "state": {
          "attention_tiles": 120,
          "attention_work": 180480,
          "query_elements": 3840,
          "request_heads": 60
        },
        "unexplained_instructions_per_call": 193409.0,
        "unexplained_share": 0.6136082068658104
      },
      {
        "calls": 12,
        "instructions_per_call": 358906.0,
        "state": {
          "attention_tiles": 144,
          "attention_work": 221184,
          "query_elements": 4608,
          "request_heads": 72
        },
        "unexplained_instructions_per_call": 231027.41666666666,
        "unexplained_share": 0.6436989536721779
      },
      {
        "calls": 12,
        "instructions_per_call": 281015.1666666667,
        "state": {
          "attention_tiles": 12,
          "attention_work": 76800,
          "query_elements": 7680,
          "request_heads": 12
        },
        "unexplained_instructions_per_call": 133757.91666666666,
        "unexplained_share": 0.4759811303185889
      },
      {
        "calls": 12,
        "instructions_per_call": 446410.1666666667,
        "state": {
          "attention_tiles": 24,
          "attention_work": 168960,
          "query_elements": 15360,
          "request_heads": 24
        },
        "unexplained_instructions_per_call": 274010.25,
        "unexplained_share": 0.6138082652687494
      },
      {
        "calls": 12,
        "instructions_per_call": 1149077.1666666667,
        "state": {
          "attention_tiles": 36,
          "attention_work": 1115136,
          "query_elements": 50688,
          "request_heads": 36
        },
        "unexplained_instructions_per_call": 797721.3333333334,
        "unexplained_share": 0.694227817307889
      },
      {
        "calls": 12,
        "instructions_per_call": 1478437.9166666667,
        "state": {
          "attention_tiles": 48,
          "attention_work": 1354752,
          "query_elements": 64512,
          "request_heads": 48
        },
        "unexplained_instructions_per_call": 1055638.9166666667,
        "unexplained_share": 0.7140231623974741
      },
      {
        "calls": 12,
        "instructions_per_call": 4391189.666666667,
        "state": {
          "attention_tiles": 240,
          "attention_work": 8125440,
          "query_elements": 176640,
          "request_heads": 60
        },
        "unexplained_instructions_per_call": 3400428.5,
        "unexplained_share": 0.7743752281557108
      },
      {
        "calls": 12,
        "instructions_per_call": 5213004.416666667,
        "state": {
          "attention_tiles": 288,
          "attention_work": 9331200,
          "query_elements": 207360,
          "request_heads": 72
        },
        "unexplained_instructions_per_call": 4064580.9166666665,
        "unexplained_share": 0.7797002633781898
      },
      {
        "calls": 12,
        "instructions_per_call": 6104044.416666667,
        "state": {
          "attention_tiles": 336,
          "attention_work": 11375616,
          "query_elements": 247296,
          "request_heads": 84
        },
        "unexplained_instructions_per_call": 4753592.666666666,
        "unexplained_share": 0.7787611528001522
      },
      {
        "calls": 12,
        "instructions_per_call": 7092678.666666667,
        "state": {
          "attention_tiles": 384,
          "attention_work": 13283328,
          "query_elements": 282624,
          "request_heads": 96
        },
        "unexplained_instructions_per_call": 5561920.833333334,
        "unexplained_share": 0.7841777549394127
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 78.41777549394126,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 78.41777549394126,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}