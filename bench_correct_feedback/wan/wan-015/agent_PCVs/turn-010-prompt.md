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
    "hypothesis": "Detailed cache and categorical predictors increased irregularity. A compact model with one combined spatial-temporal work term and one execution-path offset may fit more robustly; the combined term gives multi-frame chunks three times the spatial work of initial chunks.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] * (2 * x.shape[2] + 1)",
        "name": "effective_spatiotemporal_work",
        "rationale": "Combines temporal work in the early encoder stages with spatial work in later stages into one predictor."
      },
      {
        "expression": "int(x.shape[2] > 1)",
        "name": "temporal_chunk",
        "rationale": "Captures the additional fixed overhead of cached multi-frame execution."
      }
    ]
  },
  "case_id": "wan-015",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-015",
    "distinct_states": 6,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "effective_spatiotemporal_work": 2.068029720568781,
        "temporal_chunk": 3400697.2888888908
      },
      "constant": 9105525.125925925,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 38.440462284721434,
    "max_unexplained_share": 0.8333835973317523,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "effective_spatiotemporal_work",
      "temporal_chunk"
    ],
    "raw_files": [
      "run.1556992.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 12896705.666666666,
        "state": {
          "effective_spatiotemporal_work": 768,
          "temporal_chunk": 0
        },
        "unexplained_instructions_per_call": 3807695.444444444,
        "unexplained_share": 0.2952455877384225
      },
      {
        "calls": 9,
        "instructions_per_call": 22428800.0,
        "state": {
          "effective_spatiotemporal_work": 2304,
          "temporal_chunk": 1
        },
        "unexplained_instructions_per_call": 9894298.111111106,
        "unexplained_share": 0.4411425538196919
      },
      {
        "calls": 6,
        "instructions_per_call": 19089159.833333332,
        "state": {
          "effective_spatiotemporal_work": 3072,
          "temporal_chunk": 0
        },
        "unexplained_instructions_per_call": 10025596.666666666,
        "unexplained_share": 0.5251984243518173
      },
      {
        "calls": 3,
        "instructions_per_call": 30014324.666666668,
        "state": {
          "effective_spatiotemporal_work": 6912,
          "temporal_chunk": 0
        },
        "unexplained_instructions_per_call": 20936337.666666668,
        "unexplained_share": 0.6975448523057446
      },
      {
        "calls": 3,
        "instructions_per_call": 42081418.333333336,
        "state": {
          "effective_spatiotemporal_work": 9216,
          "temporal_chunk": 1
        },
        "unexplained_instructions_per_call": 29502797.000000015,
        "unexplained_share": 0.7010884653721473
      },
      {
        "calls": 6,
        "instructions_per_call": 75505776.33333333,
        "state": {
          "effective_spatiotemporal_work": 20736,
          "temporal_chunk": 1
        },
        "unexplained_instructions_per_call": 62925275.500000015,
        "unexplained_share": 0.8333835973317523
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 83.33835973317522,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 83.33835973317522,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}