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

This is iteration 6. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Native tensor dimensions and scheduler metadata cardinality may expose kernel work missing from earlier predictors. All expressions use constant-time scalar or shape access.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "query.shape[0]",
        "name": "query_rows",
        "rationale": "Observes the query tensor's native row count directly."
      },
      {
        "expression": "0 if attn_metadata is None or attn_metadata.scheduler_metadata is None else attn_metadata.scheduler_metadata.numel()",
        "name": "scheduler_elements",
        "rationale": "Tests whether scheduler metadata cardinality captures native task partitioning."
      },
      {
        "expression": "0 if attn_metadata is None else query.shape[0] * ((attn_metadata.max_seq_len + 31) // 32)",
        "name": "query_context_blocks",
        "rationale": "Captures query work across rounded context blocks using tensor dimensions."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel()",
        "name": "sequence_count",
        "rationale": "Measures per-sequence overhead from the native kernel's sequence-length tensor."
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
        "query_context_blocks": 19.947133435826295,
        "query_rows": 3869.403995537684,
        "scheduler_elements": 75.98185975857655,
        "sequence_count": 1963.8453377395729
      },
      "constant": -234144.7956084101,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 125.40260178316385,
    "max_unexplained_share": 0.7781944286029712,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_rows",
      "scheduler_elements",
      "query_context_blocks",
      "sequence_count"
    ],
    "raw_files": [
      "run.1796453.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 36,
        "instructions_per_call": 123441.30555555556,
        "state": {
          "query_context_blocks": 1,
          "query_rows": 1,
          "scheduler_elements": 4328,
          "sequence_count": 1
        },
        "unexplained_instructions_per_call": 23553.05555555556,
        "unexplained_share": 0.19080368155175864
      },
      {
        "calls": 24,
        "instructions_per_call": 138707.79166666666,
        "state": {
          "query_context_blocks": 2,
          "query_rows": 1,
          "scheduler_elements": 4328,
          "sequence_count": 1
        },
        "unexplained_instructions_per_call": 38851.625,
        "unexplained_share": 0.28009691837186507
      },
      {
        "calls": 48,
        "instructions_per_call": 152290.1875,
        "state": {
          "query_context_blocks": 2,
          "query_rows": 2,
          "scheduler_elements": 4368,
          "sequence_count": 2
        },
        "unexplained_instructions_per_call": 42664.50000000001,
        "unexplained_share": 0.2801526526454635
      },
      {
        "calls": 36,
        "instructions_per_call": 183034.63888888888,
        "state": {
          "query_context_blocks": 4,
          "query_rows": 2,
          "scheduler_elements": 4368,
          "sequence_count": 2
        },
        "unexplained_instructions_per_call": 73647.30555555556,
        "unexplained_share": 0.40236813098674257
      },
      {
        "calls": 12,
        "instructions_per_call": 180379.66666666666,
        "state": {
          "query_context_blocks": 3,
          "query_rows": 3,
          "scheduler_elements": 4408,
          "sequence_count": 3
        },
        "unexplained_instructions_per_call": 61808.08333333333,
        "unexplained_share": 0.3426554914726161
      },
      {
        "calls": 24,
        "instructions_per_call": 227432.29166666666,
        "state": {
          "query_context_blocks": 6,
          "query_rows": 3,
          "scheduler_elements": 4408,
          "sequence_count": 3
        },
        "unexplained_instructions_per_call": 108669.625,
        "unexplained_share": 0.4778108869397944
      },
      {
        "calls": 24,
        "instructions_per_call": 271710.9166666667,
        "state": {
          "query_context_blocks": 8,
          "query_rows": 4,
          "scheduler_elements": 4448,
          "sequence_count": 4
        },
        "unexplained_instructions_per_call": 143327.0,
        "unexplained_share": 0.5274981283723418
      },
      {
        "calls": 24,
        "instructions_per_call": 314962.7083333333,
        "state": {
          "query_context_blocks": 10,
          "query_rows": 5,
          "scheduler_elements": 4488,
          "sequence_count": 5
        },
        "unexplained_instructions_per_call": 177464.83333333337,
        "unexplained_share": 0.563447127669215
      },
      {
        "calls": 12,
        "instructions_per_call": 358713.5833333333,
        "state": {
          "query_context_blocks": 12,
          "query_rows": 6,
          "scheduler_elements": 4528,
          "sequence_count": 6
        },
        "unexplained_instructions_per_call": 211806.33333333334,
        "unexplained_share": 0.5904608667592971
      },
      {
        "calls": 12,
        "instructions_per_call": 281051.0,
        "state": {
          "query_context_blocks": 10,
          "query_rows": 10,
          "scheduler_elements": 4328,
          "sequence_count": 1
        },
        "unexplained_instructions_per_call": 129804.16666666664,
        "unexplained_share": 0.4618527123784176
      },
      {
        "calls": 12,
        "instructions_per_call": 446054.8333333333,
        "state": {
          "query_context_blocks": 20,
          "query_rows": 20,
          "scheduler_elements": 4368,
          "sequence_count": 2
        },
        "unexplained_instructions_per_call": 266435.6666666667,
        "unexplained_share": 0.5973159503185147
      },
      {
        "calls": 12,
        "instructions_per_call": 1149240.6666666667,
        "state": {
          "query_context_blocks": 66,
          "query_rows": 66,
          "scheduler_elements": 4488,
          "sequence_count": 3
        },
        "unexplained_instructions_per_call": 780281.0833333334,
        "unexplained_share": 0.6789535960265938
      },
      {
        "calls": 12,
        "instructions_per_call": 1478381.3333333333,
        "state": {
          "query_context_blocks": 84,
          "query_rows": 84,
          "scheduler_elements": 4528,
          "sequence_count": 4
        },
        "unexplained_instructions_per_call": 1034318.0833333334,
        "unexplained_share": 0.6996287493709337
      },
      {
        "calls": 12,
        "instructions_per_call": 4391378.25,
        "state": {
          "query_context_blocks": 460,
          "query_rows": 230,
          "scheduler_elements": 4608,
          "sequence_count": 5
        },
        "unexplained_instructions_per_call": 3369911.1666666665,
        "unexplained_share": 0.7673925985917215
      },
      {
        "calls": 12,
        "instructions_per_call": 5212766.083333333,
        "state": {
          "query_context_blocks": 540,
          "query_rows": 270,
          "scheduler_elements": 4648,
          "sequence_count": 6
        },
        "unexplained_instructions_per_call": 4029652.5833333335,
        "unexplained_share": 0.7730353748688736
      },
      {
        "calls": 12,
        "instructions_per_call": 6103745.333333333,
        "state": {
          "query_context_blocks": 644,
          "query_rows": 322,
          "scheduler_elements": 4688,
          "sequence_count": 7
        },
        "unexplained_instructions_per_call": 4714449.333333333,
        "unexplained_share": 0.772386309695315
      },
      {
        "calls": 12,
        "instructions_per_call": 7092114.083333333,
        "state": {
          "query_context_blocks": 736,
          "query_rows": 368,
          "scheduler_elements": 4728,
          "sequence_count": 8
        },
        "unexplained_instructions_per_call": 5519043.666666668,
        "unexplained_share": 0.7781944286029712
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 77.81944286029712,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 77.81944286029712,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}