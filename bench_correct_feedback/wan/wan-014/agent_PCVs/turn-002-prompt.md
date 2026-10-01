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

This is iteration 2. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Instruction count is primarily affine in spatial volume, with distinct costs for initial and cached chunks and a smaller contribution from spatial boundaries.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "latent_volume",
        "rationale": "Models spatially proportional convolution, normalization, activation, and copying work."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_latent_volume",
        "rationale": "Allows a separate volume slope for subsequent chunks, which activate temporal convolutions and temporal upsampling."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "has_cached_features",
        "rationale": "Captures additional fixed dispatch, slicing, and concatenation overhead for subsequent chunks."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4]) * (4 if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 1)",
        "name": "expanded_spatial_boundary",
        "rationale": "Models convolution padding and boundary work, with greater temporal extent after cached temporal upsampling."
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
        "cached_latent_volume": 2089046.2848389247,
        "expanded_spatial_boundary": 449025.555555557,
        "has_cached_features": 3049170.764705874,
        "latent_volume": 793864.759937305
      },
      "constant": 13447353.495876133,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 41.09209956321865,
    "max_unexplained_share": 0.20465773071375684,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "latent_volume",
      "cached_latent_volume",
      "has_cached_features",
      "expanded_spatial_boundary"
    ],
    "raw_files": [
      "run.1545336.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 21301132.0,
        "state": {
          "cached_latent_volume": 0,
          "expanded_spatial_boundary": 4,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 2954831.111111111,
        "unexplained_share": 0.13871709311557295
      },
      {
        "calls": 9,
        "instructions_per_call": 41598767.777777776,
        "state": {
          "cached_latent_volume": 4,
          "expanded_spatial_boundary": 16,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 6250236.666666666,
        "unexplained_share": 0.1502505242476333
      },
      {
        "calls": 6,
        "instructions_per_call": 34750703.333333336,
        "state": {
          "cached_latent_volume": 0,
          "expanded_spatial_boundary": 8,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 5097147.833333333,
        "unexplained_share": 0.14667754446408804
      },
      {
        "calls": 3,
        "instructions_per_call": 89346023.0,
        "state": {
          "cached_latent_volume": 16,
          "expanded_spatial_boundary": 32,
          "has_cached_features": 1,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 12293415.33333333,
        "unexplained_share": 0.13759331328416632
      },
      {
        "calls": 3,
        "instructions_per_call": 59558903.333333336,
        "state": {
          "cached_latent_volume": 0,
          "expanded_spatial_boundary": 12,
          "has_cached_features": 0,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 12189190.00000001,
        "unexplained_share": 0.20465773071375684
      },
      {
        "calls": 6,
        "instructions_per_call": 170071133.5,
        "state": {
          "cached_latent_volume": 36,
          "expanded_spatial_boundary": 48,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 28227697.0,
        "unexplained_share": 0.16597582681484274
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 20.465773071375683,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 20.465773071375683,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}