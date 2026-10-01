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
    "hypothesis": "Observed mean costs approximately follow a shared token-plus-request cost with a smaller block-dependent increment. This constrained two-feature model tests whether fitting fewer overlapping terms improves attribution.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else (attn_metadata.num_actual_tokens + attn_metadata.seq_lens.numel()) * (4 + (attn_metadata.max_seq_len + 31) // 32)",
        "name": "combined_query_work",
        "rationale": "Combines token and request work with a modest increase for additional context blocks, reducing the number of independently fitted terms."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel() * ((attn_metadata.max_seq_len - 1) // 32)",
        "name": "additional_request_blocks",
        "rationale": "Preserves the stronger context-block effect observed during decode."
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
        "additional_request_blocks": 169.8474386362353,
        "combined_query_work": 3.335505092623762
      },
      "constant": 92168.96330204271,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 124.89459085697308,
    "max_unexplained_share": 0.9859059598858899,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "combined_query_work",
      "additional_request_blocks"
    ],
    "raw_files": [
      "run.1800147.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 36,
        "instructions_per_call": 123467.97222222222,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 10
        },
        "unexplained_instructions_per_call": 32778.72222222222,
        "unexplained_share": 0.26548360382258374
      },
      {
        "calls": 24,
        "instructions_per_call": 138565.79166666666,
        "state": {
          "additional_request_blocks": 1,
          "combined_query_work": 12
        },
        "unexplained_instructions_per_call": 48004.24999999999,
        "unexplained_share": 0.34643651526546204
      },
      {
        "calls": 48,
        "instructions_per_call": 152258.14583333334,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 20
        },
        "unexplained_instructions_per_call": 60874.8125,
        "unexplained_share": 0.3998131736520391
      },
      {
        "calls": 36,
        "instructions_per_call": 182990.69444444444,
        "state": {
          "additional_request_blocks": 2,
          "combined_query_work": 24
        },
        "unexplained_instructions_per_call": 91797.02777777781,
        "unexplained_share": 0.5016486114579295
      },
      {
        "calls": 12,
        "instructions_per_call": 180302.91666666666,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 30
        },
        "unexplained_instructions_per_call": 89026.58333333334,
        "unexplained_share": 0.4937611935469708
      },
      {
        "calls": 24,
        "instructions_per_call": 227402.5,
        "state": {
          "additional_request_blocks": 3,
          "combined_query_work": 36
        },
        "unexplained_instructions_per_call": 135798.08333333334,
        "unexplained_share": 0.5971705822641938
      },
      {
        "calls": 24,
        "instructions_per_call": 271518.4166666667,
        "state": {
          "additional_request_blocks": 4,
          "combined_query_work": 48
        },
        "unexplained_instructions_per_call": 179449.3333333333,
        "unexplained_share": 0.6609103556818274
      },
      {
        "calls": 12,
        "instructions_per_call": 281332.5,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 55
        },
        "unexplained_instructions_per_call": 174204.00000000003,
        "unexplained_share": 0.6192103649596119
      },
      {
        "calls": 24,
        "instructions_per_call": 315170.7083333333,
        "state": {
          "additional_request_blocks": 5,
          "combined_query_work": 60
        },
        "unexplained_instructions_per_call": 222628.875,
        "unexplained_share": 0.7063755263847092
      },
      {
        "calls": 12,
        "instructions_per_call": 358694.1666666667,
        "state": {
          "additional_request_blocks": 6,
          "combined_query_work": 72
        },
        "unexplained_instructions_per_call": 265908.5833333334,
        "unexplained_share": 0.7413239691194682
      },
      {
        "calls": 12,
        "instructions_per_call": 446298.6666666667,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 110
        },
        "unexplained_instructions_per_call": 354387.8333333334,
        "unexplained_share": 0.7940598074831803
      },
      {
        "calls": 12,
        "instructions_per_call": 1149483.6666666667,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 345
        },
        "unexplained_instructions_per_call": 1056057.75,
        "unexplained_share": 0.9187235805293449
      },
      {
        "calls": 12,
        "instructions_per_call": 1477962.25,
        "state": {
          "additional_request_blocks": 0,
          "combined_query_work": 440
        },
        "unexplained_instructions_per_call": 1384916.4166666667,
        "unexplained_share": 0.9370445129208589
      },
      {
        "calls": 12,
        "instructions_per_call": 4391135.666666667,
        "state": {
          "additional_request_blocks": 5,
          "combined_query_work": 1410
        },
        "unexplained_instructions_per_call": 4294460.583333334,
        "unexplained_share": 0.9779840363240885
      },
      {
        "calls": 12,
        "instructions_per_call": 5213022.333333333,
        "state": {
          "additional_request_blocks": 6,
          "combined_query_work": 1656
        },
        "unexplained_instructions_per_call": 5115138.583333333,
        "unexplained_share": 0.9812232245056562
      },
      {
        "calls": 12,
        "instructions_per_call": 6104057.166666667,
        "state": {
          "additional_request_blocks": 7,
          "combined_query_work": 1974
        },
        "unexplained_instructions_per_call": 6004787.5,
        "unexplained_share": 0.9837371007583672
      },
      {
        "calls": 12,
        "instructions_per_call": 7092063.916666667,
        "state": {
          "additional_request_blocks": 8,
          "combined_query_work": 2256
        },
        "unexplained_instructions_per_call": 6992108.083333334,
        "unexplained_share": 0.9859059598858899
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 98.59059598858899,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 98.59059598858899,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}