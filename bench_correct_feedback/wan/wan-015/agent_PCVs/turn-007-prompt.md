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
    "hypothesis": "Explicit shape regimes may capture kernel-dependent instruction costs missed by polynomial work estimates. The two remaining regimes\u2014medium initial chunks and small temporal chunks\u2014have similar observed total costs and share the fitted baseline.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "int(x.shape[2] == 1 and x.shape[3] * x.shape[4] < 1024)",
        "name": "initial_small_spatial",
        "rationale": "Separates initial chunks below the medium spatial size into their own execution regime."
      },
      {
        "expression": "int(x.shape[2] == 1 and x.shape[3] * x.shape[4] > 1024)",
        "name": "initial_large_spatial",
        "rationale": "Separates large initial chunks, whose instruction scaling remains poorly explained by area."
      },
      {
        "expression": "int(x.shape[2] > 1 and x.shape[3] * x.shape[4] == 1024)",
        "name": "temporal_medium_spatial",
        "rationale": "Allows an independent cost for medium spatial inputs with multiple temporal frames."
      },
      {
        "expression": "int(x.shape[2] > 1 and x.shape[3] * x.shape[4] > 1024)",
        "name": "temporal_large_spatial",
        "rationale": "Allows an independent cost for large spatial inputs with multiple temporal frames."
      }
    ]
  },
  "case_id": "wan-015",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-015",
    "distinct_states": 5,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 5; need 6"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 37.24773410987109,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_small_spatial",
      "initial_large_spatial",
      "temporal_medium_spatial",
      "temporal_large_spatial"
    ],
    "raw_files": [
      "run.1554925.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 15,
        "instructions_per_call": 21070363.4,
        "state": {
          "initial_large_spatial": 0,
          "initial_small_spatial": 0,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        }
      },
      {
        "calls": 6,
        "instructions_per_call": 75482049.33333333,
        "state": {
          "initial_large_spatial": 0,
          "initial_small_spatial": 0,
          "temporal_large_spatial": 1,
          "temporal_medium_spatial": 0
        }
      },
      {
        "calls": 3,
        "instructions_per_call": 42060152.666666664,
        "state": {
          "initial_large_spatial": 0,
          "initial_small_spatial": 0,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 1
        }
      },
      {
        "calls": 3,
        "instructions_per_call": 30000579.0,
        "state": {
          "initial_large_spatial": 1,
          "initial_small_spatial": 0,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        }
      },
      {
        "calls": 9,
        "instructions_per_call": 12873656.111111112,
        "state": {
          "initial_large_spatial": 0,
          "initial_small_spatial": 1,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 5; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "success": false,
      "threshold_percent": 10.0,
      "valid": false
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": null,
      "iteration": 6,
      "reasons": [
        "insufficient state points: 5; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}