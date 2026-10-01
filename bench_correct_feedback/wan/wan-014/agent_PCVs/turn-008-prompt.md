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
    "hypothesis": "Test whether the nonlinear spatial instruction patterns chiefly arise before temporal upsampling. Retain separate volume slopes and cache overhead, but use an unscaled boundary feature shared by both paths.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "latent_volume",
        "rationale": "Captures area-dependent work common to initial and cached chunks."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_latent_volume",
        "rationale": "Allows an independently fitted area slope for cached temporal expansion."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "has_cached_features",
        "rationale": "Captures fixed cache-dependent execution overhead."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4])",
        "name": "spatial_boundary",
        "rationale": "Captures boundary and row work without imposing temporal expansion on its contribution."
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
        "cached_latent_volume": 1640276.068027208,
        "has_cached_features": 6164793.785714347,
        "latent_volume": 600836.7091836672,
        "spatial_boundary": -62978.39583332213
      },
      "constant": 14453112.178571902,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 41.14001574693248,
    "max_unexplained_share": 0.40957910984319273,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "latent_volume",
      "cached_latent_volume",
      "has_cached_features",
      "spatial_boundary"
    ],
    "raw_files": [
      "run.1549363.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 21299489.333333332,
        "state": {
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 4,
          "spatial_boundary": 4
        },
        "unexplained_instructions_per_call": 4863831.000000001,
        "unexplained_share": 0.22835434802599655
      },
      {
        "calls": 9,
        "instructions_per_call": 41592264.44444445,
        "state": {
          "cached_latent_volume": 4,
          "has_cached_features": 1,
          "latent_volume": 4,
          "spatial_boundary": 4
        },
        "unexplained_instructions_per_call": 12090552.111111106,
        "unexplained_share": 0.29069232638825615
      },
      {
        "calls": 6,
        "instructions_per_call": 34749159.0,
        "state": {
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 16,
          "spatial_boundary": 8
        },
        "unexplained_instructions_per_call": 11385191.5,
        "unexplained_share": 0.3276393394153798
      },
      {
        "calls": 3,
        "instructions_per_call": 89344336.66666667,
        "state": {
          "cached_latent_volume": 16,
          "has_cached_features": 1,
          "latent_volume": 16,
          "spatial_boundary": 8
        },
        "unexplained_instructions_per_call": 33195878.333333343,
        "unexplained_share": 0.37154988857529164
      },
      {
        "calls": 3,
        "instructions_per_call": 59563363.333333336,
        "state": {
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 36,
          "spatial_boundary": 12
        },
        "unexplained_instructions_per_call": 24395909.333333332,
        "unexplained_share": 0.40957910984319273
      },
      {
        "calls": 6,
        "instructions_per_call": 170073557.66666666,
        "state": {
          "cached_latent_volume": 36,
          "has_cached_features": 1,
          "latent_volume": 36,
          "spatial_boundary": 12
        },
        "unexplained_instructions_per_call": 69351545.50000001,
        "unexplained_share": 0.4077738271102944
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 40.95791098431928,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 40.95791098431928,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}