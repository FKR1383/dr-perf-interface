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
    "hypothesis": "The previous features isolated the observed cost regimes, but the fitted model systematically underpredicted them, especially the sparse admission indicators. Uniform feature scaling tests whether numerical conditioning or regularization causes this remaining error without changing the information represented.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "16 * len(self.running)",
        "name": "running_requests_scaled",
        "rationale": "Preserves the decode-work predictor while increasing its numerical scale for fitting."
      },
      {
        "expression": "16 * (len(self.waiting) + len(self.skipped_waiting))",
        "name": "waiting_requests_scaled",
        "rationale": "Preserves the admission-work predictor on the same numerical scale."
      },
      {
        "expression": "16 * int(len(self.waiting) + len(self.skipped_waiting) == 1)",
        "name": "singleton_admission_scaled",
        "rationale": "Preserves the singleton admission indicator while reducing potential attenuation of this sparsely observed feature."
      },
      {
        "expression": "16 * int(len(self.waiting) + len(self.skipped_waiting) == 2)",
        "name": "pair_admission_scaled",
        "rationale": "Preserves the pair admission indicator while reducing potential attenuation of this sparsely observed feature."
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
        "pair_admission_scaled": 3663.54896551724,
        "running_requests_scaled": 4106.196353067086,
        "singleton_admission_scaled": 6873.340009578536,
        "waiting_requests_scaled": 8648.49916666666
      },
      "constant": 72999.5197861444,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 99.05128876585513,
    "max_unexplained_share": 0.17349253427360328,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests_scaled",
      "waiting_requests_scaled",
      "singleton_admission_scaled",
      "pair_admission_scaled"
    ],
    "raw_files": [
      "run.2260652.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 392795.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 16,
          "waiting_requests_scaled": 16
        },
        "unexplained_instructions_per_call": 68147.0,
        "unexplained_share": 0.17349253427360328
      },
      {
        "calls": 1,
        "instructions_per_call": 484539.0,
        "state": {
          "pair_admission_scaled": 16,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 32
        },
        "unexplained_instructions_per_call": 76118.0,
        "unexplained_share": 0.15709364984036372
      },
      {
        "calls": 1,
        "instructions_per_call": 524141.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 48
        },
        "unexplained_instructions_per_call": 38865.0,
        "unexplained_share": 0.07414989478022135
      },
      {
        "calls": 1,
        "instructions_per_call": 660328.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 64
        },
        "unexplained_instructions_per_call": 39889.0,
        "unexplained_share": 0.060407857913037155
      },
      {
        "calls": 1,
        "instructions_per_call": 815778.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 80
        },
        "unexplained_instructions_per_call": 52453.0,
        "unexplained_share": 0.06429813012853987
      },
      {
        "calls": 1,
        "instructions_per_call": 961845.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 96
        },
        "unexplained_instructions_per_call": 58146.0,
        "unexplained_share": 0.060452567721410416
      },
      {
        "calls": 1,
        "instructions_per_call": 1112347.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 112
        },
        "unexplained_instructions_per_call": 67115.0,
        "unexplained_share": 0.060336387835810225
      },
      {
        "calls": 1,
        "instructions_per_call": 1258363.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 0,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 128
        },
        "unexplained_instructions_per_call": 73762.0,
        "unexplained_share": 0.058617425973268446
      },
      {
        "calls": 5,
        "instructions_per_call": 146179.2,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 16,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 0
        },
        "unexplained_instructions_per_call": 10738.8,
        "unexplained_share": 0.07346325605831745
      },
      {
        "calls": 7,
        "instructions_per_call": 222297.2857142857,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 32,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 0
        },
        "unexplained_instructions_per_call": 17147.85714285714,
        "unexplained_share": 0.07713930058910815
      },
      {
        "calls": 3,
        "instructions_per_call": 287228.3333333333,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 48,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 0
        },
        "unexplained_instructions_per_call": 19217.666666666668,
        "unexplained_share": 0.06690728050273592
      },
      {
        "calls": 2,
        "instructions_per_call": 359390.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 64,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 0
        },
        "unexplained_instructions_per_call": 24431.0,
        "unexplained_share": 0.06797907565597262
      },
      {
        "calls": 2,
        "instructions_per_call": 430216.5,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 80,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 0
        },
        "unexplained_instructions_per_call": 27682.0,
        "unexplained_share": 0.06434434755524253
      },
      {
        "calls": 1,
        "instructions_per_call": 501726.0,
        "state": {
          "pair_admission_scaled": 0,
          "running_requests_scaled": 96,
          "singleton_admission_scaled": 0,
          "waiting_requests_scaled": 0
        },
        "unexplained_instructions_per_call": 31660.0,
        "unexplained_share": 0.06310217130465633
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.349253427360328,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.349253427360328,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}