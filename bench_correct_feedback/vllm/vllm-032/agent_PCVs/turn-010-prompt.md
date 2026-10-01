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
    "hypothesis": "Admission-only singleton and pair indicators produced the best result so far but left systematic unexplained work. Applying those cardinality distinctions to the entire active population tests whether the missing behavior follows container size across both scheduling paths.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "len(self.running)",
        "name": "running_requests",
        "rationale": "Captures per-request decode work."
      },
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting)",
        "name": "waiting_requests",
        "rationale": "Captures per-request admission work."
      },
      {
        "expression": "int(len(self.running) + len(self.waiting) + len(self.skipped_waiting) == 1)",
        "name": "singleton_population",
        "rationale": "Tests whether singleton-specific container and allocation behavior also occurs during decode, rather than only admission."
      },
      {
        "expression": "int(len(self.running) + len(self.waiting) + len(self.skipped_waiting) == 2)",
        "name": "pair_population",
        "rationale": "Tests whether two-request container and allocation behavior is shared across admission and decode."
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
        "pair_population": 13.108655785805823,
        "running_requests": 42739.17244033421,
        "singleton_population": 501.45003903486554,
        "waiting_requests": 94801.4079253884
      },
      "constant": 53277.319037539135,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 129.98254034202546,
    "max_unexplained_share": 0.6018404673717973,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests",
      "waiting_requests",
      "singleton_population",
      "pair_population"
    ],
    "raw_files": [
      "run.2265304.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 392835.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 1,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 236424.0,
        "unexplained_share": 0.6018404673717973
      },
      {
        "calls": 1,
        "instructions_per_call": 481897.0,
        "state": {
          "pair_population": 1,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 236459.0,
        "unexplained_share": 0.49068369381838856
      },
      {
        "calls": 1,
        "instructions_per_call": 523073.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 190739.0,
        "unexplained_share": 0.3646508231164675
      },
      {
        "calls": 1,
        "instructions_per_call": 661297.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 234556.0,
        "unexplained_share": 0.35469085751182905
      },
      {
        "calls": 1,
        "instructions_per_call": 815776.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 290915.0,
        "unexplained_share": 0.35661137371043033
      },
      {
        "calls": 1,
        "instructions_per_call": 960731.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 339812.0,
        "unexplained_share": 0.3537015043753142
      },
      {
        "calls": 1,
        "instructions_per_call": 1111409.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 393554.0,
        "unexplained_share": 0.35410366480746513
      },
      {
        "calls": 1,
        "instructions_per_call": 1259738.0,
        "state": {
          "pair_population": 0,
          "running_requests": 0,
          "singleton_population": 0,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 445321.0,
        "unexplained_share": 0.35350287123195456
      },
      {
        "calls": 5,
        "instructions_per_call": 145631.2,
        "state": {
          "pair_population": 0,
          "running_requests": 1,
          "singleton_population": 1,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 53819.00000000004,
        "unexplained_share": 0.36955679826850313
      },
      {
        "calls": 7,
        "instructions_per_call": 221624.7142857143,
        "state": {
          "pair_population": 1,
          "running_requests": 2,
          "singleton_population": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 85183.85714285709,
        "unexplained_share": 0.3843608210275669
      },
      {
        "calls": 3,
        "instructions_per_call": 286886.3333333333,
        "state": {
          "pair_population": 0,
          "running_requests": 3,
          "singleton_population": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 106639.0,
        "unexplained_share": 0.3717116767500253
      },
      {
        "calls": 2,
        "instructions_per_call": 358829.0,
        "state": {
          "pair_population": 0,
          "running_requests": 4,
          "singleton_population": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 134164.0,
        "unexplained_share": 0.3738939717804302
      },
      {
        "calls": 2,
        "instructions_per_call": 430477.5,
        "state": {
          "pair_population": 0,
          "running_requests": 5,
          "singleton_population": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 160156.0,
        "unexplained_share": 0.37204267354275194
      },
      {
        "calls": 1,
        "instructions_per_call": 500507.0,
        "state": {
          "pair_population": 0,
          "running_requests": 6,
          "singleton_population": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 185685.0,
        "unexplained_share": 0.3709938122743538
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 60.18404673717973,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 60.18404673717973,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}