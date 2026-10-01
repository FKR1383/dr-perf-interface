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
    "hypothesis": "This candidate retains six distinct states, correcting the previous validity failure. It models initial chunks with spatial area while allowing independent costs for all three multi-frame spatial regimes.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4] if x.shape[2] == 1 else 0",
        "name": "initial_area",
        "rationale": "Preserves distinct initial-chunk spatial states and models their approximately affine instruction growth."
      },
      {
        "expression": "int(x.shape[2] > 1)",
        "name": "temporal_chunk",
        "rationale": "Provides a separate baseline for multi-frame chunks."
      },
      {
        "expression": "int(x.shape[2] > 1 and x.shape[3] * x.shape[4] == 1024)",
        "name": "temporal_medium_spatial",
        "rationale": "Captures the medium multi-frame execution regime independently."
      },
      {
        "expression": "int(x.shape[2] > 1 and x.shape[3] * x.shape[4] > 1024)",
        "name": "temporal_large_spatial",
        "rationale": "Captures the large multi-frame execution regime independently."
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
        "initial_area": 3813.1710778061224,
        "temporal_chunk": 7859584.007936446,
        "temporal_large_spatial": 28648449.72222172,
        "temporal_medium_spatial": 11117285.000000084
      },
      "constant": 9637313.842592664,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 39.429089481942356,
    "max_unexplained_share": 0.38876562217879296,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_area",
      "temporal_chunk",
      "temporal_medium_spatial",
      "temporal_large_spatial"
    ],
    "raw_files": [
      "run.1555597.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 22421843.111111112,
        "state": {
          "initial_area": 0,
          "temporal_chunk": 1,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        },
        "unexplained_instructions_per_call": 4921066.333333333,
        "unexplained_share": 0.21947644129642072
      },
      {
        "calls": 6,
        "instructions_per_call": 75501445.66666667,
        "state": {
          "initial_area": 0,
          "temporal_chunk": 1,
          "temporal_large_spatial": 1,
          "temporal_medium_spatial": 0
        },
        "unexplained_instructions_per_call": 29352366.5,
        "unexplained_share": 0.38876562217879296
      },
      {
        "calls": 3,
        "instructions_per_call": 42075433.333333336,
        "state": {
          "initial_area": 0,
          "temporal_chunk": 1,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 1
        },
        "unexplained_instructions_per_call": 13435611.0,
        "unexplained_share": 0.3193219875731127
      },
      {
        "calls": 9,
        "instructions_per_call": 12886668.0,
        "state": {
          "initial_area": 256,
          "temporal_chunk": 0,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        },
        "unexplained_instructions_per_call": 2268934.666666666,
        "unexplained_share": 0.1760683728848036
      },
      {
        "calls": 6,
        "instructions_per_call": 19079666.333333332,
        "state": {
          "initial_area": 1024,
          "temporal_chunk": 0,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        },
        "unexplained_instructions_per_call": 5563551.0,
        "unexplained_share": 0.29159582263134964
      },
      {
        "calls": 3,
        "instructions_per_call": 30012758.333333332,
        "state": {
          "initial_area": 2304,
          "temporal_chunk": 0,
          "temporal_large_spatial": 0,
          "temporal_medium_spatial": 0
        },
        "unexplained_instructions_per_call": 11601510.333333332,
        "unexplained_share": 0.38655261887236286
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 38.8765622178793,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 38.8765622178793,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}