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

This is iteration 4. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The measurements suggest nearly linear decode and admission costs, with exceptional overhead in singleton and two-request admission states. Explicit cardinality indicators may isolate those deviations and prevent them from degrading the fit across all states.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "len(self.running)",
        "name": "running_requests",
        "rationale": "Captures the approximately linear cost of decode scheduling and cached-request output construction."
      },
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting)",
        "name": "waiting_requests",
        "rationale": "Captures the approximately linear admission cost evident for batches of three through eight requests."
      },
      {
        "expression": "int(len(self.waiting) + len(self.skipped_waiting) == 1)",
        "name": "singleton_admission",
        "rationale": "Separates singleton admission, whose measured cost substantially exceeds the larger-batch linear trend."
      },
      {
        "expression": "int(len(self.waiting) + len(self.skipped_waiting) == 2)",
        "name": "pair_admission",
        "rationale": "Separates two-request admission, which also shows excess cost relative to the larger-batch trend."
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
        "pair_admission": 58890.766934865904,
        "running_requests": 65677.80534600043,
        "singleton_admission": 109077.38544061291,
        "waiting_requests": 138399.77459770103
      },
      "constant": 73470.20458049898,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 126.2634957912378,
    "max_unexplained_share": 0.1738978716467484,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests",
      "waiting_requests",
      "singleton_admission",
      "pair_admission"
    ],
    "raw_files": [
      "run.2259711.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 392604.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 1,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 68273.0,
        "unexplained_share": 0.1738978716467484
      },
      {
        "calls": 1,
        "instructions_per_call": 485265.0,
        "state": {
          "pair_admission": 1,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 75641.0,
        "unexplained_share": 0.1558756555696372
      },
      {
        "calls": 1,
        "instructions_per_call": 525152.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 38908.0,
        "unexplained_share": 0.07408902565352507
      },
      {
        "calls": 1,
        "instructions_per_call": 662783.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 41269.0,
        "unexplained_share": 0.06226623193413229
      },
      {
        "calls": 1,
        "instructions_per_call": 816739.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 52522.0,
        "unexplained_share": 0.06430695730214915
      },
      {
        "calls": 1,
        "instructions_per_call": 963284.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 58313.0,
        "unexplained_share": 0.06053562604590131
      },
      {
        "calls": 1,
        "instructions_per_call": 1113100.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 67570.0,
        "unexplained_share": 0.06070433923277334
      },
      {
        "calls": 1,
        "instructions_per_call": 1260698.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 74616.0,
        "unexplained_share": 0.059186260309764906
      },
      {
        "calls": 5,
        "instructions_per_call": 146190.8,
        "state": {
          "pair_admission": 0,
          "running_requests": 1,
          "singleton_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 10703.199999999997,
        "unexplained_share": 0.07321390949362065
      },
      {
        "calls": 7,
        "instructions_per_call": 222064.85714285713,
        "state": {
          "pair_admission": 0,
          "running_requests": 2,
          "singleton_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 16938.142857142855,
        "unexplained_share": 0.07627565691876376
      },
      {
        "calls": 3,
        "instructions_per_call": 287015.6666666667,
        "state": {
          "pair_admission": 0,
          "running_requests": 3,
          "singleton_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 18931.666666666664,
        "unexplained_share": 0.06596039472874302
      },
      {
        "calls": 2,
        "instructions_per_call": 359170.5,
        "state": {
          "pair_admission": 0,
          "running_requests": 4,
          "singleton_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 23993.0,
        "unexplained_share": 0.06680114318965505
      },
      {
        "calls": 2,
        "instructions_per_call": 430312.5,
        "state": {
          "pair_admission": 0,
          "running_requests": 5,
          "singleton_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 27878.5,
        "unexplained_share": 0.06478663761801016
      },
      {
        "calls": 1,
        "instructions_per_call": 500981.0,
        "state": {
          "pair_admission": 0,
          "running_requests": 6,
          "singleton_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 31627.0,
        "unexplained_share": 0.06313013866793352
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.38978716467484,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.38978716467484,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}