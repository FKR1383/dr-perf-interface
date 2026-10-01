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
    "hypothesis": "Observed instruction means closely follow separate affine functions of area for initial and cached chunks. Removing perimeter and attention terms should give a better-conditioned fit with three predictors.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_area",
        "rationale": "Models spatially proportional computation for initial chunks."
      },
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_area",
        "rationale": "Models the larger spatially proportional computation for cached chunks."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "warm_cache",
        "rationale": "Allows an independent fixed cost for cached execution."
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
        "cached_area": 13494.813884017158,
        "initial_area": 3619.9625141723377,
        "warm_cache": 3450335.571428568
      },
      "constant": 9373742.853174612,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 38.90505385538563,
    "max_unexplained_share": 0.417056086896743,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_area",
      "cached_area",
      "warm_cache"
    ],
    "raw_files": [
      "run.1554334.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 22409323.555555556,
        "state": {
          "cached_area": 256,
          "initial_area": 0,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 6047667.888888885,
        "unexplained_share": 0.26987284439425174
      },
      {
        "calls": 3,
        "instructions_per_call": 42063673.666666664,
        "state": {
          "cached_area": 1024,
          "initial_area": 0,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 15321739.66666666,
        "unexplained_share": 0.3642511062653181
      },
      {
        "calls": 6,
        "instructions_per_call": 75487539.5,
        "state": {
          "cached_area": 2304,
          "initial_area": 0,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 31482537.83333332,
        "unexplained_share": 0.417056086896743
      },
      {
        "calls": 9,
        "instructions_per_call": 12874227.777777778,
        "state": {
          "cached_area": 0,
          "initial_area": 256,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 2648576.9999999995,
        "unexplained_share": 0.20572705763150406
      },
      {
        "calls": 6,
        "instructions_per_call": 19075886.833333332,
        "state": {
          "cached_area": 0,
          "initial_area": 1024,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 6100159.5,
        "unexplained_share": 0.3197837958097204
      },
      {
        "calls": 3,
        "instructions_per_call": 30005387.666666668,
        "state": {
          "cached_area": 0,
          "initial_area": 2304,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 12382534.666666666,
        "unexplained_share": 0.41267704334387145
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 41.7056086896743,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 41.7056086896743,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}