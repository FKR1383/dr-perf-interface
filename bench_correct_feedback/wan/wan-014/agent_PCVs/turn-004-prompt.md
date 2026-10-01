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

This is iteration 4. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The allocation-state experiment did not explain the instruction counts. Explicitly gating both volume and fixed overhead by execution path should let Dr. Perf explain path-specific instructions without requiring cancellation between shared and cached features.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_volume",
        "rationale": "Models volume-dependent work exclusively on the initial-chunk path."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_volume",
        "rationale": "Models volume-dependent work exclusively on the cached path, including temporal upsampling."
      },
      {
        "expression": "int(feat_cache is None or feat_cache[feat_idx[0]] is None)",
        "name": "initial_path",
        "rationale": "Provides a fixed-cost feature for operations specific to initial chunks."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "cached_path",
        "rationale": "Provides a fixed-cost feature for cache handling and additional temporal operations."
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
        "cached_path": 0.0,
        "cached_volume": 2477469.8339002286,
        "initial_path": -5676487.928571488,
        "initial_volume": 666546.5150226769
      },
      "constant": 19222470.300265078,
      "dependent_columns": [
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 40.97044583503157,
    "max_unexplained_share": 0.37045217973971023,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_volume",
      "cached_volume",
      "initial_path",
      "cached_path"
    ],
    "raw_files": [
      "run.1547106.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 41598266.11111111,
        "state": {
          "cached_path": 1,
          "cached_volume": 4,
          "initial_path": 0,
          "initial_volume": 0
        },
        "unexplained_instructions_per_call": 12337547.111111104,
        "unexplained_share": 0.29658801350414177
      },
      {
        "calls": 3,
        "instructions_per_call": 89356059.66666667,
        "state": {
          "cached_path": 1,
          "cached_volume": 16,
          "initial_path": 0,
          "initial_volume": 0
        },
        "unexplained_instructions_per_call": 30507673.666666664,
        "unexplained_share": 0.34141695348331513
      },
      {
        "calls": 6,
        "instructions_per_call": 170063667.0,
        "state": {
          "cached_path": 1,
          "cached_volume": 36,
          "initial_path": 0,
          "initial_volume": 0
        },
        "unexplained_instructions_per_call": 61502996.333333306,
        "unexplained_share": 0.3616468903574407
      },
      {
        "calls": 9,
        "instructions_per_call": 21299755.444444444,
        "state": {
          "cached_path": 0,
          "cached_volume": 0,
          "initial_path": 1,
          "initial_volume": 4
        },
        "unexplained_instructions_per_call": 5172609.888888885,
        "unexplained_share": 0.24284832294814176
      },
      {
        "calls": 6,
        "instructions_per_call": 34758943.833333336,
        "state": {
          "cached_path": 0,
          "cached_volume": 0,
          "initial_path": 1,
          "initial_volume": 16
        },
        "unexplained_instructions_per_call": 10685369.166666668,
        "unexplained_share": 0.3074135168750309
      },
      {
        "calls": 3,
        "instructions_per_call": 59566210.0,
        "state": {
          "cached_path": 0,
          "cached_volume": 0,
          "initial_path": 1,
          "initial_volume": 36
        },
        "unexplained_instructions_per_call": 22066432.333333325,
        "unexplained_share": 0.37045217973971023
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 37.04521797397102,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 37.04521797397102,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}