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
    "hypothesis": "Removing the boundary feature substantially increased irregularity. Separate area and boundary terms for each cache regime should explain instruction patterns better than fixed path indicators or a boundary term with a prescribed temporal multiplier.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_volume",
        "rationale": "Captures spatial-area work on the initial path."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_volume",
        "rationale": "Captures spatial-area work after cached temporal upsampling."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4]) if feat_cache is None or feat_cache[feat_idx[0]] is None else 0",
        "name": "initial_boundary",
        "rationale": "Captures row traversal and padding work on the initial path."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * (x.shape[3] + x.shape[4]) if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_boundary",
        "rationale": "Allows cached boundary work to scale independently across temporally expanded decoder stages."
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
        "cached_boundary": 143645.73026315783,
        "cached_volume": 2770305.4163011615,
        "initial_boundary": -322511.6834795206,
        "initial_volume": 853431.9027777802
      },
      "constant": 10784692.325536039,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 41.15713305072859,
    "max_unexplained_share": 0.4518468402311925,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_volume",
      "cached_volume",
      "initial_boundary",
      "cached_boundary"
    ],
    "raw_files": [
      "run.1547659.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 41596821.44444445,
        "state": {
          "cached_boundary": 4,
          "cached_volume": 4,
          "initial_boundary": 0,
          "initial_volume": 0
        },
        "unexplained_instructions_per_call": 18795392.333333332,
        "unexplained_share": 0.4518468402311925
      },
      {
        "calls": 3,
        "instructions_per_call": 89351729.33333333,
        "state": {
          "cached_boundary": 8,
          "cached_volume": 16,
          "initial_boundary": 0,
          "initial_volume": 0
        },
        "unexplained_instructions_per_call": 33041175.66666666,
        "unexplained_share": 0.36978775803436414
      },
      {
        "calls": 6,
        "instructions_per_call": 170082939.16666666,
        "state": {
          "cached_boundary": 12,
          "cached_volume": 36,
          "initial_boundary": 0,
          "initial_volume": 0
        },
        "unexplained_instructions_per_call": 57594702.999999985,
        "unexplained_share": 0.33862716203159055
      },
      {
        "calls": 9,
        "instructions_per_call": 21311306.888888888,
        "state": {
          "cached_boundary": 0,
          "cached_volume": 0,
          "initial_boundary": 4,
          "initial_volume": 4
        },
        "unexplained_instructions_per_call": 8634208.555555556,
        "unexplained_share": 0.40514683592948436
      },
      {
        "calls": 6,
        "instructions_per_call": 34768980.0,
        "state": {
          "cached_boundary": 0,
          "cached_volume": 0,
          "initial_boundary": 8,
          "initial_volume": 16
        },
        "unexplained_instructions_per_call": 12962272.666666666,
        "unexplained_share": 0.37281141599974077
      },
      {
        "calls": 3,
        "instructions_per_call": 59580372.333333336,
        "state": {
          "cached_boundary": 0,
          "cached_volume": 0,
          "initial_boundary": 12,
          "initial_volume": 36
        },
        "unexplained_instructions_per_call": 22319735.999999996,
        "unexplained_share": 0.3746155843929295
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 45.184684023119246,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 45.184684023119246,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}