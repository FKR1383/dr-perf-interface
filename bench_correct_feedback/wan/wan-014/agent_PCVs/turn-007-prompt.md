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
    "hypothesis": "The best result used fourfold temporal scaling, but constraining boundary work to that ratio left substantial irregularity. Apply that scaling to dominant volume work while allowing independent boundary slopes and fixed overhead for each cache regime.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] * (4 if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 1)",
        "name": "expanded_volume",
        "rationale": "Models the dominant decoder stages, whose temporal extent is four times larger for cached chunks."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4])",
        "name": "spatial_boundary",
        "rationale": "Captures spatial row and boundary work shared across both cache regimes."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4]) if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_boundary",
        "rationale": "Allows additional cached boundary work to have an independently fitted coefficient."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "has_cached_features",
        "rationale": "Preserves the fixed overhead difference between initial and cached execution."
      }
    ]
  },
  "case_id": "wan-014",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-014",
    "distinct_states": 6,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "cached_boundary": 1386853.3672385681,
        "expanded_volume": 660929.3292483599,
        "has_cached_features": 2151853.815904148,
        "spatial_boundary": 580931.5073529375
      },
      "constant": 12558829.116013475,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 41.10446790466085,
    "max_unexplained_share": 0.26481878280154697,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "expanded_volume",
      "spatial_boundary",
      "cached_boundary",
      "has_cached_features"
    ],
    "raw_files": [
      "run.1548857.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 21306208.666666668,
        "state": {
          "cached_boundary": 0,
          "expanded_volume": 4,
          "has_cached_features": 0,
          "spatial_boundary": 4
        },
        "unexplained_instructions_per_call": 4031611.1111111115,
        "unexplained_share": 0.18922236115233976
      },
      {
        "calls": 9,
        "instructions_per_call": 41632128.333333336,
        "state": {
          "cached_boundary": 4,
          "expanded_volume": 16,
          "has_cached_features": 1,
          "spatial_boundary": 4
        },
        "unexplained_instructions_per_call": 8477482.555555558,
        "unexplained_share": 0.2036283729642509
      },
      {
        "calls": 6,
        "instructions_per_call": 34759290.5,
        "state": {
          "cached_boundary": 0,
          "expanded_volume": 16,
          "has_cached_features": 0,
          "spatial_boundary": 8
        },
        "unexplained_instructions_per_call": 6970572.833333334,
        "unexplained_share": 0.20053840953207414
      },
      {
        "calls": 3,
        "instructions_per_call": 59580079.0,
        "state": {
          "cached_boundary": 0,
          "expanded_volume": 36,
          "has_cached_features": 0,
          "spatial_boundary": 12
        },
        "unexplained_instructions_per_call": 15777924.00000001,
        "unexplained_share": 0.26481878280154697
      },
      {
        "calls": 3,
        "instructions_per_call": 89373963.66666667,
        "state": {
          "cached_boundary": 8,
          "expanded_volume": 64,
          "has_cached_features": 1,
          "spatial_boundary": 8
        },
        "unexplained_instructions_per_call": 16690637.999999998,
        "unexplained_share": 0.18675056263869177
      },
      {
        "calls": 6,
        "instructions_per_call": 170093825.33333334,
        "state": {
          "cached_boundary": 12,
          "expanded_volume": 144,
          "has_cached_features": 1,
          "spatial_boundary": 12
        },
        "unexplained_instructions_per_call": 36759325.50000001,
        "unexplained_share": 0.21611205126325223
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 26.481878280154696,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 26.481878280154696,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}