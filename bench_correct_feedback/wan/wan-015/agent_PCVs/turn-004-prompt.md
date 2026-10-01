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
    "hypothesis": "Input layout did not explain the residual. Separating initial and cached spatial work supplies direct predictors for mutually exclusive execution paths, while temporal perimeter accounts for convolution boundary costs.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_spatial_work",
        "rationale": "Separately models spatial work on the initial-cache execution path."
      },
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_spatial_work",
        "rationale": "Separately models spatial work on the populated-cache path, including its larger temporal chunks."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "warm_cache",
        "rationale": "Captures fixed overhead from cache concatenations and temporal downsampling."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4])",
        "name": "spatial_boundary_work",
        "rationale": "Captures convolution padding and boundary work that scales with spatial perimeter rather than area."
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
        "cached_spatial_work": 16973.82043051596,
        "initial_spatial_work": 4783.1757481638715,
        "spatial_boundary_work": 30687.347630718832,
        "warm_cache": 1820332.5812325098
      },
      "constant": 9089421.482181814,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 39.44809842808172,
    "max_unexplained_share": 0.2344710442000314,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_spatial_work",
      "cached_spatial_work",
      "warm_cache",
      "spatial_boundary_work"
    ],
    "raw_files": [
      "run.1553296.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 22515083.888888888,
        "state": {
          "cached_spatial_work": 256,
          "initial_spatial_work": 0,
          "spatial_boundary_work": 128,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 3220124.7777777775,
        "unexplained_share": 0.14302077636792185
      },
      {
        "calls": 3,
        "instructions_per_call": 42173835.0,
        "state": {
          "cached_spatial_work": 1024,
          "initial_spatial_work": 0,
          "spatial_boundary_work": 256,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 5955355.000000001,
        "unexplained_share": 0.14120970976435984
      },
      {
        "calls": 6,
        "instructions_per_call": 75588586.33333333,
        "state": {
          "cached_spatial_work": 2304,
          "initial_spatial_work": 0,
          "spatial_boundary_work": 384,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 13780741.000000002,
        "unexplained_share": 0.18231245838133794
      },
      {
        "calls": 9,
        "instructions_per_call": 12883105.222222222,
        "state": {
          "cached_spatial_work": 0,
          "initial_spatial_work": 256,
          "spatial_boundary_work": 32,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 1623963.0000000005,
        "unexplained_share": 0.1260536937320676
      },
      {
        "calls": 6,
        "instructions_per_call": 19073669.833333332,
        "state": {
          "cached_spatial_work": 0,
          "initial_spatial_work": 1024,
          "spatial_boundary_work": 64,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 3186233.166666667,
        "unexplained_share": 0.16704877427931433
      },
      {
        "calls": 3,
        "instructions_per_call": 30000944.0,
        "state": {
          "cached_spatial_work": 0,
          "initial_spatial_work": 2304,
          "spatial_boundary_work": 96,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 7034352.666666667,
        "unexplained_share": 0.2344710442000314
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 23.44710442000314,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 23.44710442000314,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}