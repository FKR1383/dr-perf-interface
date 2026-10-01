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
    "hypothesis": "Short-context costs approximately follow tokens plus requests. A reduced three-column model tests whether sharing their baseline coefficient resolves unstable attribution while retaining separate token and request costs for additional KV blocks.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens + attn_metadata.query_start_loc.numel() - 1",
        "name": "query_and_request_units",
        "rationale": "Combines token processing and request setup into a single predictor, reducing overlap between fitted columns."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens * ((attn_metadata.max_seq_len - 1) // 32)",
        "name": "additional_token_blocks",
        "rationale": "Captures additional token-dependent work when the KV context spans multiple blocks."
      },
      {
        "expression": "0 if attn_metadata is None else (attn_metadata.query_start_loc.numel() - 1) * ((attn_metadata.max_seq_len - 1) // 32)",
        "name": "additional_request_blocks",
        "rationale": "Captures additional per-request block overhead, particularly visible during decode."
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
        "additional_request_blocks": 415.89640446827485,
        "additional_token_blocks": -19.21722558729521,
        "query_and_request_units": 400.255291035617
      },
      "constant": 91850.0961658664,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 100.68462122278288,
    "max_unexplained_share": 0.9662855566878039,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_and_request_units",
      "additional_token_blocks",
      "additional_request_blocks"
    ],
    "raw_files": [
      "run.1795236.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 36,
        "instructions_per_call": 123333.75,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 2
        },
        "unexplained_instructions_per_call": 32038.027777777774,
        "unexplained_share": 0.259766915201863
      },
      {
        "calls": 24,
        "instructions_per_call": 138711.95833333334,
        "state": {
          "additional_request_blocks": 1,
          "additional_token_blocks": 1,
          "query_and_request_units": 2
        },
        "unexplained_instructions_per_call": 47280.75,
        "unexplained_share": 0.3408556159691831
      },
      {
        "calls": 48,
        "instructions_per_call": 152236.52083333334,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 4
        },
        "unexplained_instructions_per_call": 59520.020833333336,
        "unexplained_share": 0.39097071128218386
      },
      {
        "calls": 36,
        "instructions_per_call": 183026.83333333334,
        "state": {
          "additional_request_blocks": 2,
          "additional_token_blocks": 2,
          "query_and_request_units": 4
        },
        "unexplained_instructions_per_call": 90433.66666666666,
        "unexplained_share": 0.49410059180757643
      },
      {
        "calls": 12,
        "instructions_per_call": 180305.16666666666,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 6
        },
        "unexplained_instructions_per_call": 87072.66666666666,
        "unexplained_share": 0.48291831164017296
      },
      {
        "calls": 24,
        "instructions_per_call": 227658.08333333334,
        "state": {
          "additional_request_blocks": 3,
          "additional_token_blocks": 3,
          "query_and_request_units": 6
        },
        "unexplained_instructions_per_call": 133882.70833333334,
        "unexplained_share": 0.5880867763316113
      },
      {
        "calls": 24,
        "instructions_per_call": 271472.7916666667,
        "state": {
          "additional_request_blocks": 4,
          "additional_token_blocks": 4,
          "query_and_request_units": 8
        },
        "unexplained_instructions_per_call": 176872.875,
        "unexplained_share": 0.651530762674651
      },
      {
        "calls": 24,
        "instructions_per_call": 315123.2083333333,
        "state": {
          "additional_request_blocks": 5,
          "additional_token_blocks": 5,
          "query_and_request_units": 10
        },
        "unexplained_instructions_per_call": 219443.5,
        "unexplained_share": 0.6963736538499427
      },
      {
        "calls": 12,
        "instructions_per_call": 281238.0833333333,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 11
        },
        "unexplained_instructions_per_call": 169941.08333333334,
        "unexplained_share": 0.6042605657069322
      },
      {
        "calls": 12,
        "instructions_per_call": 358971.4166666667,
        "state": {
          "additional_request_blocks": 6,
          "additional_token_blocks": 6,
          "query_and_request_units": 12
        },
        "unexplained_instructions_per_call": 262207.0833333333,
        "unexplained_share": 0.7304400048564683
      },
      {
        "calls": 12,
        "instructions_per_call": 446526.0,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 22
        },
        "unexplained_instructions_per_call": 346383.4166666666,
        "unexplained_share": 0.7757295581145703
      },
      {
        "calls": 12,
        "instructions_per_call": 1149288.25,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 69
        },
        "unexplained_instructions_per_call": 1030320.25,
        "unexplained_share": 0.8964854987423738
      },
      {
        "calls": 12,
        "instructions_per_call": 1478043.75,
        "state": {
          "additional_request_blocks": 0,
          "additional_token_blocks": 0,
          "query_and_request_units": 88
        },
        "unexplained_instructions_per_call": 1352227.5,
        "unexplained_share": 0.9148765048395895
      },
      {
        "calls": 12,
        "instructions_per_call": 4391262.166666667,
        "state": {
          "additional_request_blocks": 5,
          "additional_token_blocks": 230,
          "query_and_request_units": 235
        },
        "unexplained_instructions_per_call": 4207378.833333334,
        "unexplained_share": 0.9581251753244977
      },
      {
        "calls": 12,
        "instructions_per_call": 5212958.166666667,
        "state": {
          "additional_request_blocks": 6,
          "additional_token_blocks": 270,
          "query_and_request_units": 276
        },
        "unexplained_instructions_per_call": 5012950.666666667,
        "unexplained_share": 0.9616326289976942
      },
      {
        "calls": 12,
        "instructions_per_call": 6103969.916666667,
        "state": {
          "additional_request_blocks": 7,
          "additional_token_blocks": 322,
          "query_and_request_units": 329
        },
        "unexplained_instructions_per_call": 5883193.0,
        "unexplained_share": 0.963830602103093
      },
      {
        "calls": 12,
        "instructions_per_call": 7092491.916666667,
        "state": {
          "additional_request_blocks": 8,
          "additional_token_blocks": 368,
          "query_and_request_units": 376
        },
        "unexplained_instructions_per_call": 6853372.5,
        "unexplained_share": 0.9662855566878039
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 96.6285556687804,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 96.6285556687804,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}