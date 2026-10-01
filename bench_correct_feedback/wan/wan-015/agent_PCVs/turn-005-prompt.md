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
    "hypothesis": "Separating spatial execution paths reduced irregularity. Independent area and perimeter predictors for each path should better explain their different convolution shapes and padding costs than a shared temporal-perimeter term.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_area",
        "rationale": "Captures area-dependent work exclusively on the initial-cache path."
      },
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_area",
        "rationale": "Captures area-dependent work exclusively on the populated-cache path."
      },
      {
        "expression": "x.shape[0] * (x.shape[3] + x.shape[4]) if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_perimeter",
        "rationale": "Allows initial-chunk convolution boundaries and padding to have an independent spatial scaling."
      },
      {
        "expression": "x.shape[0] * (x.shape[3] + x.shape[4]) if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_perimeter",
        "rationale": "Allows cached-chunk boundary work to scale independently of initial chunks."
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
        "cached_area": 18005.196026361522,
        "cached_perimeter": 32841.166483918794,
        "initial_area": 7664.339563916323,
        "initial_perimeter": -58839.88939144716
      },
      "constant": 10645439.76267055,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 39.452166479080915,
    "max_unexplained_share": 0.2664553829192972,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_area",
      "cached_area",
      "initial_perimeter",
      "cached_perimeter"
    ],
    "raw_files": [
      "run.1553815.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 22417389.888888888,
        "state": {
          "cached_area": 256,
          "cached_perimeter": 32,
          "initial_area": 0,
          "initial_perimeter": 0
        },
        "unexplained_instructions_per_call": 5845948.111111111,
        "unexplained_share": 0.2607773759606437
      },
      {
        "calls": 3,
        "instructions_per_call": 42067243.333333336,
        "state": {
          "cached_area": 1024,
          "cached_perimeter": 64,
          "initial_area": 0,
          "initial_perimeter": 0
        },
        "unexplained_instructions_per_call": 11026821.33333333,
        "unexplained_share": 0.26212369671952984
      },
      {
        "calls": 6,
        "instructions_per_call": 75490793.66666667,
        "state": {
          "cached_area": 2304,
          "cached_perimeter": 96,
          "initial_area": 0,
          "initial_perimeter": 0
        },
        "unexplained_instructions_per_call": 20114928.333333325,
        "unexplained_share": 0.2664553829192972
      },
      {
        "calls": 9,
        "instructions_per_call": 12884366.555555556,
        "state": {
          "cached_area": 0,
          "cached_perimeter": 0,
          "initial_area": 256,
          "initial_perimeter": 32
        },
        "unexplained_instructions_per_call": 2405452.333333333,
        "unexplained_share": 0.18669542836749983
      },
      {
        "calls": 6,
        "instructions_per_call": 19073560.5,
        "state": {
          "cached_area": 0,
          "cached_perimeter": 0,
          "initial_area": 1024,
          "initial_perimeter": 64
        },
        "unexplained_instructions_per_call": 4196468.5,
        "unexplained_share": 0.2200149521113271
      },
      {
        "calls": 3,
        "instructions_per_call": 30005194.666666668,
        "state": {
          "cached_area": 0,
          "cached_perimeter": 0,
          "initial_area": 2304,
          "initial_perimeter": 96
        },
        "unexplained_instructions_per_call": 7468430.666666667,
        "unexplained_share": 0.24890458967638315
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 26.64553829192972,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 26.64553829192972,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}