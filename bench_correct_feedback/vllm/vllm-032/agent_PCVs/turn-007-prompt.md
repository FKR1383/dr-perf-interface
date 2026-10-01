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
    "hypothesis": "The small-batch excess costs are approximately in a three-to-two ratio. Combining their indicators frees a feature for the admission-path fixed cost, which the previous candidate could not model independently.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "len(self.running)",
        "name": "running_requests",
        "rationale": "Captures per-request decode scheduling work."
      },
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting)",
        "name": "waiting_requests",
        "rationale": "Captures per-request admission work."
      },
      {
        "expression": "int(bool(self.waiting or self.skipped_waiting))",
        "name": "has_waiting_requests",
        "rationale": "Separates fixed admission-path costs from decode-path costs."
      },
      {
        "expression": "4 - len(self.waiting) - len(self.skipped_waiting) if 0 < len(self.waiting) + len(self.skipped_waiting) <= 2 else 0",
        "name": "small_admission_adjustment",
        "rationale": "Combines the two exceptional small-admission states into one feature, assigning singleton and pair batches values of three and two."
      }
    ]
  },
  "case_id": "vllm-032",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-032",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "has_waiting_requests": -959.3988697866772,
        "running_requests": 46365.855782312894,
        "small_admission_adjustment": 5611.724928366739,
        "waiting_requests": 103576.24140401158
      },
      "constant": 56241.78262317364,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 123.70308857504278,
    "max_unexplained_share": 0.5399583524367411,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests",
      "waiting_requests",
      "has_waiting_requests",
      "small_admission_adjustment"
    ],
    "raw_files": [
      "run.2262343.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 390419.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 3,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 210810.0,
        "unexplained_share": 0.5399583524367411
      },
      {
        "calls": 1,
        "instructions_per_call": 481713.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 2,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 212754.0,
        "unexplained_share": 0.44166132116010987
      },
      {
        "calls": 1,
        "instructions_per_call": 524687.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 0,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 164219.0,
        "unexplained_share": 0.31298469373169147
      },
      {
        "calls": 1,
        "instructions_per_call": 662012.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 0,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 199567.0,
        "unexplained_share": 0.30145526062971667
      },
      {
        "calls": 1,
        "instructions_per_call": 815497.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 0,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 246610.0,
        "unexplained_share": 0.30240454593947
      },
      {
        "calls": 1,
        "instructions_per_call": 961363.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 0,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 287115.0,
        "unexplained_share": 0.298654098399876
      },
      {
        "calls": 1,
        "instructions_per_call": 1111280.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 0,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 331823.0,
        "unexplained_share": 0.29859531351234614
      },
      {
        "calls": 1,
        "instructions_per_call": 1259057.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission_adjustment": 0,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 375476.0,
        "unexplained_share": 0.29822001704450235
      },
      {
        "calls": 5,
        "instructions_per_call": 146361.6,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 1,
          "small_admission_adjustment": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 46248.00000000006,
        "unexplained_share": 0.31598452052997544
      },
      {
        "calls": 7,
        "instructions_per_call": 221990.57142857142,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 2,
          "small_admission_adjustment": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 72800.28571428574,
        "unexplained_share": 0.3279431430163702
      },
      {
        "calls": 3,
        "instructions_per_call": 286961.6666666667,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 3,
          "small_admission_adjustment": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 89885.99999999999,
        "unexplained_share": 0.3132334748543649
      },
      {
        "calls": 2,
        "instructions_per_call": 359191.5,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 4,
          "small_admission_adjustment": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 113479.0,
        "unexplained_share": 0.3159289682523111
      },
      {
        "calls": 2,
        "instructions_per_call": 429978.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 5,
          "small_admission_adjustment": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 134255.0,
        "unexplained_share": 0.3122369051439841
      },
      {
        "calls": 1,
        "instructions_per_call": 499101.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 6,
          "small_admission_adjustment": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 154374.0,
        "unexplained_share": 0.3093041288236249
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 53.99583524367411,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 53.99583524367411,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}