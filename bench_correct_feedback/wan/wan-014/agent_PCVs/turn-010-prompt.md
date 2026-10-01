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
    "hypothesis": "The fourfold boundary weighting remains the best tested structure; onefold and twofold weighting performed substantially worse. Testing eightfold weighting determines whether the remaining nonlinear spatial work is more concentrated in cached execution.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "latent_volume",
        "rationale": "Captures spatial-volume work shared across decoder paths."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_latent_volume",
        "rationale": "Allows additional cached volume work to be fitted independently."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "has_cached_features",
        "rationale": "Captures fixed cache-dependent overhead."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4]) * (8 if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 1)",
        "name": "cache_weighted_boundary",
        "rationale": "Tests stronger cache dependence in nonlinear spatial work, including temporal convolution and rearrangement operations."
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
        "cache_weighted_boundary": -33600.20213675096,
        "cached_latent_volume": 1895853.9418737825,
        "has_cached_features": 6686996.009890221,
        "latent_volume": 689327.1080542455
      },
      "constant": 13983196.769699417,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 41.14392671221867,
    "max_unexplained_share": 0.35701497413960637,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "latent_volume",
      "cached_latent_volume",
      "has_cached_features",
      "cache_weighted_boundary"
    ],
    "raw_files": [
      "run.1550621.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 21301132.0,
        "state": {
          "cache_weighted_boundary": 4,
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 4839638.111111108,
        "unexplained_share": 0.22720098214081338
      },
      {
        "calls": 9,
        "instructions_per_call": 41598767.777777776,
        "state": {
          "cache_weighted_boundary": 32,
          "cached_latent_volume": 4,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 11450160.333333332,
        "unexplained_share": 0.27525239195787077
      },
      {
        "calls": 6,
        "instructions_per_call": 34750703.333333336,
        "state": {
          "cache_weighted_boundary": 8,
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 10190693.0,
        "unexplained_share": 0.2932514171655614
      },
      {
        "calls": 3,
        "instructions_per_call": 89346023.0,
        "state": {
          "cache_weighted_boundary": 64,
          "cached_latent_volume": 16,
          "has_cached_features": 1,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 29326084.66666667,
        "unexplained_share": 0.3282304425197154
      },
      {
        "calls": 3,
        "instructions_per_call": 59558903.333333336,
        "state": {
          "cache_weighted_boundary": 12,
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 21263420.333333317,
        "unexplained_share": 0.35701497413960637
      },
      {
        "calls": 6,
        "instructions_per_call": 170071133.5,
        "state": {
          "cache_weighted_boundary": 96,
          "cached_latent_volume": 36,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 59481684.666666664,
        "unexplained_share": 0.34974591773780744
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 35.70149741396064,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 35.70149741396064,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}