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
    "hypothesis": "Scaling did not help. Making admission predictors mutually exclusive may allow Dr. Perf to attribute distinct execution paths without subtractive corrections between the general request-count feature and small-batch indicators.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "len(self.running)",
        "name": "running_requests",
        "rationale": "Models repeated decode scheduling work."
      },
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting) if len(self.waiting) + len(self.skipped_waiting) >= 3 else 0",
        "name": "larger_admission_requests",
        "rationale": "Models larger admission batches independently of the exceptional singleton and pair states."
      },
      {
        "expression": "int(len(self.waiting) + len(self.skipped_waiting) == 1)",
        "name": "singleton_admission",
        "rationale": "Provides a separate predictor for the full singleton admission cost."
      },
      {
        "expression": "int(len(self.waiting) + len(self.skipped_waiting) == 2)",
        "name": "pair_admission",
        "rationale": "Provides a separate predictor for the full pair admission cost."
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
        "larger_admission_requests": 138363.9525287355,
        "pair_admission": 326584.1739846745,
        "running_requests": 65688.54723199623,
        "singleton_admission": 243147.5095402299
      },
      "constant": 73546.22930017988,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 123.54628216288984,
    "max_unexplained_share": 0.1800635518418265,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests",
      "larger_admission_requests",
      "singleton_admission",
      "pair_admission"
    ],
    "raw_files": [
      "run.2261396.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 483343.0,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 1,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 74980.0,
        "unexplained_share": 0.15512793192412014
      },
      {
        "calls": 1,
        "instructions_per_call": 390862.0,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 1
        },
        "unexplained_instructions_per_call": 70380.0,
        "unexplained_share": 0.1800635518418265
      },
      {
        "calls": 1,
        "instructions_per_call": 523830.0,
        "state": {
          "larger_admission_requests": 3,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 38402.0,
        "unexplained_share": 0.07331004333466964
      },
      {
        "calls": 1,
        "instructions_per_call": 659118.0,
        "state": {
          "larger_admission_requests": 4,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 39470.0,
        "unexplained_share": 0.05988305584129094
      },
      {
        "calls": 1,
        "instructions_per_call": 815687.0,
        "state": {
          "larger_admission_requests": 5,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 51978.0,
        "unexplained_share": 0.06372297216947187
      },
      {
        "calls": 1,
        "instructions_per_call": 962299.0,
        "state": {
          "larger_admission_requests": 6,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 58158.0,
        "unexplained_share": 0.06043651713240895
      },
      {
        "calls": 1,
        "instructions_per_call": 1111474.0,
        "state": {
          "larger_admission_requests": 7,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 66589.0,
        "unexplained_share": 0.0599105332198504
      },
      {
        "calls": 1,
        "instructions_per_call": 1257997.0,
        "state": {
          "larger_admission_requests": 8,
          "pair_admission": 0,
          "running_requests": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 73559.0,
        "unexplained_share": 0.058473112416007354
      },
      {
        "calls": 5,
        "instructions_per_call": 145441.8,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 1,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 10332.599999999999,
        "unexplained_share": 0.07104285012974261
      },
      {
        "calls": 7,
        "instructions_per_call": 221293.85714285713,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 2,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 16418.571428571428,
        "unexplained_share": 0.07419352548034062
      },
      {
        "calls": 3,
        "instructions_per_call": 286057.6666666667,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 3,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 18256.333333333332,
        "unexplained_share": 0.0638204651043554
      },
      {
        "calls": 2,
        "instructions_per_call": 358038.5,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 4,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 23348.5,
        "unexplained_share": 0.06521226069263501
      },
      {
        "calls": 2,
        "instructions_per_call": 429069.0,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 5,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 26861.0,
        "unexplained_share": 0.06260298460154427
      },
      {
        "calls": 1,
        "instructions_per_call": 499003.0,
        "state": {
          "larger_admission_requests": 0,
          "pair_admission": 0,
          "running_requests": 6,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 29932.0,
        "unexplained_share": 0.059983607312982086
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 18.006355184182652,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 18.006355184182652,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}