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
    "hypothesis": "Return to the best-performing feature structure, but account for temporal padding in the boundary term. For this workload, padded temporal extent grows from three to six frames, whereas the original boundary feature assumed a fourfold increase.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "latent_volume",
        "rationale": "Captures work proportional to the input spatial area."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_latent_volume",
        "rationale": "Captures additional area-dependent work from cached temporal upsampling."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "has_cached_features",
        "rationale": "Captures the fixed overhead difference between initial and cached chunks."
      },
      {
        "expression": "x.shape[0] * (x.shape[3] + x.shape[4]) * (4 * x.shape[2] + 2 if feat_cache is not None and feat_cache[feat_idx[0]] is not None else x.shape[2] + 2)",
        "name": "temporally_padded_boundary",
        "rationale": "Models spatial boundary work using temporal extent including the two padding frames required by causal convolutions."
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
        "cached_latent_volume": 1660754.0338718751,
        "has_cached_features": 7446082.642857195,
        "latent_volume": 665498.5188208603,
        "temporally_padded_boundary": -37168.46666666698
      },
      "constant": 15447365.959260333,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 41.10296356771141,
    "max_unexplained_share": 0.387747512573509,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "latent_volume",
      "cached_latent_volume",
      "has_cached_features",
      "temporally_padded_boundary"
    ],
    "raw_files": [
      "run.1548261.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 21296392.555555556,
        "state": {
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 4,
          "temporally_padded_boundary": 12
        },
        "unexplained_instructions_per_call": 3808868.9999999995,
        "unexplained_share": 0.17885043159604916
      },
      {
        "calls": 9,
        "instructions_per_call": 41595350.222222224,
        "state": {
          "cached_latent_volume": 4,
          "has_cached_features": 1,
          "latent_volume": 4,
          "temporally_padded_boundary": 24
        },
        "unexplained_instructions_per_call": 10033467.555555549,
        "unexplained_share": 0.2412160854987871
      },
      {
        "calls": 6,
        "instructions_per_call": 34753604.5,
        "state": {
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 16,
          "temporally_padded_boundary": 24
        },
        "unexplained_instructions_per_call": 9829326.0,
        "unexplained_share": 0.2828289652660345
      },
      {
        "calls": 3,
        "instructions_per_call": 89345979.0,
        "state": {
          "cached_latent_volume": 16,
          "has_cached_features": 1,
          "latent_volume": 16,
          "temporally_padded_boundary": 48
        },
        "unexplained_instructions_per_call": 30784789.33333334,
        "unexplained_share": 0.3445570766350139
      },
      {
        "calls": 3,
        "instructions_per_call": 59579205.0,
        "state": {
          "cached_latent_volume": 0,
          "has_cached_features": 0,
          "latent_volume": 36,
          "temporally_padded_boundary": 36
        },
        "unexplained_instructions_per_call": 21711375.999999985,
        "unexplained_share": 0.3644119789782355
      },
      {
        "calls": 6,
        "instructions_per_call": 170075930.5,
        "state": {
          "cached_latent_volume": 36,
          "has_cached_features": 1,
          "latent_volume": 36,
          "temporally_padded_boundary": 72
        },
        "unexplained_instructions_per_call": 65946518.999999985,
        "unexplained_share": 0.387747512573509
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 38.7747512573509,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 38.7747512573509,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}