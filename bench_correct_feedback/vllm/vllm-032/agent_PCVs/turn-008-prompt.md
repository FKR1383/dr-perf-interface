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

This is iteration 8. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Separate singleton and pair indicators proved necessary. Including setup units within the mutually exclusive decode and larger-admission predictors tests whether phase-specific fixed work explains the remaining error without requiring a fifth feature.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "len(self.running) + 1 if self.running else 0",
        "name": "decode_work",
        "rationale": "Represents decode processing with one setup unit plus one unit per running request."
      },
      {
        "expression": "2 * (len(self.waiting) + len(self.skipped_waiting)) + 1 if len(self.waiting) + len(self.skipped_waiting) >= 3 else 0",
        "name": "larger_admission_work",
        "rationale": "Combines admission setup and per-request work, using the observed approximate two-to-one ratio between admission and decode slopes."
      },
      {
        "expression": "int(len(self.waiting) + len(self.skipped_waiting) == 1)",
        "name": "singleton_admission",
        "rationale": "Retains an independent feature for the exceptional singleton admission path."
      },
      {
        "expression": "int(len(self.waiting) + len(self.skipped_waiting) == 2)",
        "name": "pair_admission",
        "rationale": "Retains an independent feature for the exceptional pair admission path."
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
        "decode_work": 62309.125601972446,
        "larger_admission_work": 66815.15627722243,
        "pair_admission": 364556.5193389042,
        "singleton_admission": 289395.5478975485
      },
      "constant": 22069.05979780978,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 129.23134310916066,
    "max_unexplained_share": 0.1769124488217921,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "decode_work",
      "larger_admission_work",
      "singleton_admission",
      "pair_admission"
    ],
    "raw_files": [
      "run.2263308.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 485220.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 0,
          "pair_admission": 1,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 80391.0,
        "unexplained_share": 0.16567948559416348
      },
      {
        "calls": 1,
        "instructions_per_call": 394455.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 1
        },
        "unexplained_instructions_per_call": 69784.0,
        "unexplained_share": 0.1769124488217921
      },
      {
        "calls": 1,
        "instructions_per_call": 522657.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 7,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 43963.0,
        "unexplained_share": 0.08411443834101523
      },
      {
        "calls": 1,
        "instructions_per_call": 659364.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 9,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 47576.0,
        "unexplained_share": 0.07215437906831432
      },
      {
        "calls": 1,
        "instructions_per_call": 814959.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 11,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 61947.0,
        "unexplained_share": 0.07601241289439101
      },
      {
        "calls": 1,
        "instructions_per_call": 961471.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 13,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 69317.0,
        "unexplained_share": 0.07209473816682979
      },
      {
        "calls": 1,
        "instructions_per_call": 1110635.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 15,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 80622.0,
        "unexplained_share": 0.07259090520287943
      },
      {
        "calls": 1,
        "instructions_per_call": 1257075.0,
        "state": {
          "decode_work": 0,
          "larger_admission_work": 17,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 88856.0,
        "unexplained_share": 0.0706847244595589
      },
      {
        "calls": 5,
        "instructions_per_call": 145516.6,
        "state": {
          "decode_work": 2,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 11845.599999999999,
        "unexplained_share": 0.08140377111614756
      },
      {
        "calls": 7,
        "instructions_per_call": 221295.85714285713,
        "state": {
          "decode_work": 3,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 18913.14285714286,
        "unexplained_share": 0.08546541766000397
      },
      {
        "calls": 3,
        "instructions_per_call": 286431.3333333333,
        "state": {
          "decode_work": 4,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 21773.0,
        "unexplained_share": 0.07601472837003401
      },
      {
        "calls": 2,
        "instructions_per_call": 358331.0,
        "state": {
          "decode_work": 5,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 27814.5,
        "unexplained_share": 0.07762236591308036
      },
      {
        "calls": 2,
        "instructions_per_call": 430060.5,
        "state": {
          "decode_work": 6,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 32533.5,
        "unexplained_share": 0.07564865873522446
      },
      {
        "calls": 1,
        "instructions_per_call": 500039.0,
        "state": {
          "decode_work": 7,
          "larger_admission_work": 0,
          "pair_admission": 0,
          "singleton_admission": 0
        },
        "unexplained_instructions_per_call": 36218.0,
        "unexplained_share": 0.07243035043266625
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.69124488217921,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.69124488217921,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}