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
    "hypothesis": "Warm stochastic execution requires independent fixed and per-row features. An explicitly nonzero baseline combined with penalty-row cardinality may improve attribution for greedy calls while preserving those features and the compilation indicator.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "1 + (logits.shape[0] if not sampling_metadata.no_penalties else 0)",
        "name": "baseline_and_penalty_rows",
        "rationale": "Provides an explicit nonzero baseline for every call plus the number of rows receiving penalties."
      },
      {
        "expression": "int(not sampling_metadata.all_greedy)",
        "name": "random_sampling",
        "rationale": "Captures fixed stochastic-path overhead."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.all_greedy else 0",
        "name": "random_rows",
        "rationale": "Captures stochastic work proportional to batch size."
      },
      {
        "expression": "int(not sampling_metadata.all_greedy and (not getattr(getattr(getattr(getattr(torch, '_dynamo', None), 'convert_frame', None), 'output_codes', None), 'seen', {})))",
        "name": "cold_dynamo_sampling",
        "rationale": "Separates initial compilation from subsequent sampling."
      }
    ]
  },
  "case_id": "vllm-055",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-055",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "baseline_and_penalty_rows": 2679333.454509706,
        "cold_dynamo_sampling": 16069467123.350374,
        "random_rows": 3463970.390359272,
        "random_sampling": 321094.62488846626
      },
      "constant": -2457130.550826859,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 154.841346767731,
    "max_unexplained_share": 0.9563589819768318,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "baseline_and_penalty_rows",
      "random_sampling",
      "random_rows",
      "cold_dynamo_sampling"
    ],
    "raw_files": [
      "run.2359702.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 819038.3333333334,
        "state": {
          "baseline_and_penalty_rows": 1,
          "cold_dynamo_sampling": 0,
          "random_rows": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 783294.6666666677,
        "unexplained_share": 0.9563589819768318
      },
      {
        "calls": 1,
        "instructions_per_call": 31493125.0,
        "state": {
          "baseline_and_penalty_rows": 1,
          "cold_dynamo_sampling": 0,
          "random_rows": 1,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 27602648.0,
        "unexplained_share": 0.8764658318283752
      },
      {
        "calls": 3,
        "instructions_per_call": 41843856.333333336,
        "state": {
          "baseline_and_penalty_rows": 1,
          "cold_dynamo_sampling": 0,
          "random_rows": 2,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 34372129.33333337,
        "unexplained_share": 0.821437896629812
      },
      {
        "calls": 1,
        "instructions_per_call": 16909125896.0,
        "state": {
          "baseline_and_penalty_rows": 1,
          "cold_dynamo_sampling": 1,
          "random_rows": 2,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 832162689.0,
        "unexplained_share": 0.04921382063852604
      },
      {
        "calls": 2,
        "instructions_per_call": 4598105.0,
        "state": {
          "baseline_and_penalty_rows": 2,
          "cold_dynamo_sampling": 0,
          "random_rows": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 1764464.0,
        "unexplained_share": 0.3837372134825107
      },
      {
        "calls": 2,
        "instructions_per_call": 8807136.0,
        "state": {
          "baseline_and_penalty_rows": 3,
          "cold_dynamo_sampling": 0,
          "random_rows": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 3322868.5,
        "unexplained_share": 0.3772927430665315
      },
      {
        "calls": 2,
        "instructions_per_call": 49122027.0,
        "state": {
          "baseline_and_penalty_rows": 3,
          "cold_dynamo_sampling": 0,
          "random_rows": 2,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 36205190.5,
        "unexplained_share": 0.7370459386783855
      },
      {
        "calls": 1,
        "instructions_per_call": 12909213.0,
        "state": {
          "baseline_and_penalty_rows": 4,
          "cold_dynamo_sampling": 0,
          "random_rows": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 4779602.0,
        "unexplained_share": 0.37024735744928833
      },
      {
        "calls": 3,
        "instructions_per_call": 71583226.0,
        "state": {
          "baseline_and_penalty_rows": 4,
          "cold_dynamo_sampling": 0,
          "random_rows": 3,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 52503030.00000009,
        "unexplained_share": 0.7334543710002688
      },
      {
        "calls": 3,
        "instructions_per_call": 93350295.33333333,
        "state": {
          "baseline_and_penalty_rows": 5,
          "cold_dynamo_sampling": 0,
          "random_rows": 4,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 68158070.99999991,
        "unexplained_share": 0.7301323553034563
      },
      {
        "calls": 3,
        "instructions_per_call": 117290039.66666667,
        "state": {
          "baseline_and_penalty_rows": 6,
          "cold_dynamo_sampling": 0,
          "random_rows": 5,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 85938733.66666654,
        "unexplained_share": 0.7327027419455291
      },
      {
        "calls": 2,
        "instructions_per_call": 139711585.5,
        "state": {
          "baseline_and_penalty_rows": 7,
          "cold_dynamo_sampling": 0,
          "random_rows": 6,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 102220146.0,
        "unexplained_share": 0.7316511772031962
      },
      {
        "calls": 1,
        "instructions_per_call": 162178688.0,
        "state": {
          "baseline_and_penalty_rows": 8,
          "cold_dynamo_sampling": 0,
          "random_rows": 7,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 118564309.0,
        "unexplained_share": 0.7310720690994861
      },
      {
        "calls": 1,
        "instructions_per_call": 185135209.0,
        "state": {
          "baseline_and_penalty_rows": 9,
          "cold_dynamo_sampling": 0,
          "random_rows": 8,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 135389867.0,
        "unexplained_share": 0.7313026394671367
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "73e1b2a01ca6fdec7ae22f87cbd54fa068b0c3201906791034d854c14e349916",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 95.63589819768318,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 95.63589819768318,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "73e1b2a01ca6fdec7ae22f87cbd54fa068b0c3201906791034d854c14e349916"
  }
}