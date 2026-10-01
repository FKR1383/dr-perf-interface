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
    "hypothesis": "The observed costs follow token and request counts interacting with 32-token KV block boundaries. Smaller-scale features should also avoid the numerical imbalance of the previous candidate.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens",
        "name": "query_tokens",
        "rationale": "Captures token-dependent work without large, constant head-dimension multipliers that can impair numerical fitting."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens * ((attn_metadata.max_seq_len + 31) // 32)",
        "name": "token_kv_blocks",
        "rationale": "Models token processing across rounded KV blocks; measurements show a substantial cost step beyond sequence length 32."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.query_start_loc.numel() - 1",
        "name": "requests",
        "rationale": "Captures per-request setup in both prefill and decode."
      },
      {
        "expression": "0 if attn_metadata is None else (attn_metadata.query_start_loc.numel() - 1) * ((attn_metadata.max_seq_len + 31) // 32)",
        "name": "request_kv_blocks",
        "rationale": "Captures per-request KV block overhead, including the observed decode cost increase for longer contexts."
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
        "query_tokens": 4056.885501458005,
        "request_kv_blocks": 278.1427179485438,
        "requests": 4338.236526110665,
        "token_kv_blocks": 86.66770011150167
      },
      "constant": 91150.43705606065,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 143.7125064190477,
    "max_unexplained_share": 0.762624572736417,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_tokens",
      "token_kv_blocks",
      "requests",
      "request_kv_blocks"
    ],
    "raw_files": [
      "run.1793220.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 36,
        "instructions_per_call": 123300.19444444444,
        "state": {
          "query_tokens": 1,
          "request_kv_blocks": 1,
          "requests": 1,
          "token_kv_blocks": 1
        },
        "unexplained_instructions_per_call": 24268.52777777778,
        "unexplained_share": 0.19682473241120874
      },
      {
        "calls": 24,
        "instructions_per_call": 138514.95833333334,
        "state": {
          "query_tokens": 1,
          "request_kv_blocks": 2,
          "requests": 1,
          "token_kv_blocks": 2
        },
        "unexplained_instructions_per_call": 39162.125,
        "unexplained_share": 0.28272848991339383
      },
      {
        "calls": 48,
        "instructions_per_call": 152282.27083333334,
        "state": {
          "query_tokens": 2,
          "request_kv_blocks": 2,
          "requests": 2,
          "token_kv_blocks": 2
        },
        "unexplained_instructions_per_call": 44037.87500000001,
        "unexplained_share": 0.28918583075371684
      },
      {
        "calls": 36,
        "instructions_per_call": 183108.41666666666,
        "state": {
          "query_tokens": 2,
          "request_kv_blocks": 4,
          "requests": 2,
          "token_kv_blocks": 4
        },
        "unexplained_instructions_per_call": 74312.83333333331,
        "unexplained_share": 0.40584061992417053
      },
      {
        "calls": 12,
        "instructions_per_call": 180450.41666666666,
        "state": {
          "query_tokens": 3,
          "request_kv_blocks": 3,
          "requests": 3,
          "token_kv_blocks": 3
        },
        "unexplained_instructions_per_call": 63834.0,
        "unexplained_share": 0.35374814411160965
      },
      {
        "calls": 24,
        "instructions_per_call": 227308.66666666666,
        "state": {
          "query_tokens": 3,
          "request_kv_blocks": 6,
          "requests": 3,
          "token_kv_blocks": 6
        },
        "unexplained_instructions_per_call": 109592.04166666667,
        "unexplained_share": 0.48212874270815315
      },
      {
        "calls": 24,
        "instructions_per_call": 271550.625,
        "state": {
          "query_tokens": 4,
          "request_kv_blocks": 8,
          "requests": 4,
          "token_kv_blocks": 8
        },
        "unexplained_instructions_per_call": 144598.41666666663,
        "unexplained_share": 0.5324915627303992
      },
      {
        "calls": 24,
        "instructions_per_call": 315200.4583333333,
        "state": {
          "query_tokens": 5,
          "request_kv_blocks": 10,
          "requests": 5,
          "token_kv_blocks": 10
        },
        "unexplained_instructions_per_call": 179078.58333333334,
        "unexplained_share": 0.5681418874840364
      },
      {
        "calls": 12,
        "instructions_per_call": 359071.4166666667,
        "state": {
          "query_tokens": 6,
          "request_kv_blocks": 12,
          "requests": 6,
          "token_kv_blocks": 12
        },
        "unexplained_instructions_per_call": 213745.0,
        "unexplained_share": 0.595271553453735
      },
      {
        "calls": 12,
        "instructions_per_call": 281535.1666666667,
        "state": {
          "query_tokens": 10,
          "request_kv_blocks": 1,
          "requests": 1,
          "token_kv_blocks": 10
        },
        "unexplained_instructions_per_call": 128171.83333333333,
        "unexplained_share": 0.4552604736767638
      },
      {
        "calls": 12,
        "instructions_per_call": 446597.6666666667,
        "state": {
          "query_tokens": 20,
          "request_kv_blocks": 2,
          "requests": 2,
          "token_kv_blocks": 20
        },
        "unexplained_instructions_per_call": 262749.3333333333,
        "unexplained_share": 0.5883356608073037
      },
      {
        "calls": 12,
        "instructions_per_call": 1149147.1666666667,
        "state": {
          "query_tokens": 66,
          "request_kv_blocks": 3,
          "requests": 3,
          "token_kv_blocks": 66
        },
        "unexplained_instructions_per_call": 771853.3333333334,
        "unexplained_share": 0.6716749218224588
      },
      {
        "calls": 12,
        "instructions_per_call": 1478328.0833333333,
        "state": {
          "query_tokens": 84,
          "request_kv_blocks": 4,
          "requests": 4,
          "token_kv_blocks": 84
        },
        "unexplained_instructions_per_call": 1021445.8333333333,
        "unexplained_share": 0.6909466476684781
      },
      {
        "calls": 12,
        "instructions_per_call": 4391370.416666667,
        "state": {
          "query_tokens": 230,
          "request_kv_blocks": 10,
          "requests": 5,
          "token_kv_blocks": 460
        },
        "unexplained_instructions_per_call": 3304488.9166666665,
        "unexplained_share": 0.7524960554739507
      },
      {
        "calls": 12,
        "instructions_per_call": 5212775.083333333,
        "state": {
          "query_tokens": 270,
          "request_kv_blocks": 12,
          "requests": 6,
          "token_kv_blocks": 540
        },
        "unexplained_instructions_per_call": 3950519.0,
        "unexplained_share": 0.7578533385472336
      },
      {
        "calls": 12,
        "instructions_per_call": 6103809.416666667,
        "state": {
          "query_tokens": 322,
          "request_kv_blocks": 14,
          "requests": 7,
          "token_kv_blocks": 644
        },
        "unexplained_instructions_per_call": 4619197.25,
        "unexplained_share": 0.7567728503100243
      },
      {
        "calls": 12,
        "instructions_per_call": 7092835.75,
        "state": {
          "query_tokens": 368,
          "request_kv_blocks": 16,
          "requests": 8,
          "token_kv_blocks": 736
        },
        "unexplained_instructions_per_call": 5409170.833333334,
        "unexplained_share": 0.762624572736417
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 76.2624572736417,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 76.2624572736417,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}