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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "A populated-cache flag hides differences between the first continuation and later continuations. Actual cached element and frame cardinalities may explain variation that remains even with explicit input-shape regimes.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4]",
        "name": "spatial_sites",
        "rationale": "Models spatial computation shared by all chunks."
      },
      {
        "expression": "x.numel()",
        "name": "input_sites",
        "rationale": "Models computation proportional to input temporal volume."
      },
      {
        "expression": "sum((v.numel() for v in feat_cache if v is not None)) if feat_cache is not None else 0",
        "name": "cached_elements",
        "rationale": "Measures cached tensor volume using metadata, distinguishing partially filled histories from mature histories."
      },
      {
        "expression": "sum((v.shape[2] for v in feat_cache if v is not None)) if feat_cache is not None else 0",
        "name": "cached_frames",
        "rationale": "Captures cache occupancy and temporal history lengths that affect concatenation, padding, and short-history branches."
      }
    ]
  },
  "case_id": "wan-015",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-015",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "cached_elements": -5.809034253111945,
        "cached_frames": 21328.567014446195,
        "input_sites": 1084.822784569992,
        "spatial_sites": 99.3883916139742
      },
      "constant": 5437492.400703607,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 39.9503922984004,
    "max_unexplained_share": 0.5851451850931816,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "spatial_sites",
      "input_sites",
      "cached_elements",
      "cached_frames"
    ],
    "raw_files": [
      "run.1556430.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 12881604.888888888,
        "state": {
          "cached_elements": 0,
          "cached_frames": 0,
          "input_sites": 768,
          "spatial_sites": 256
        },
        "unexplained_instructions_per_call": 6789161.666666667,
        "unexplained_share": 0.5270431538016433
      },
      {
        "calls": 6,
        "instructions_per_call": 22513898.833333332,
        "state": {
          "cached_elements": 8448,
          "cached_frames": 16,
          "input_sites": 3072,
          "spatial_sites": 256
        },
        "unexplained_instructions_per_call": 13173899.499999998,
        "unexplained_share": 0.5851451850931816
      },
      {
        "calls": 3,
        "instructions_per_call": 22154917.333333332,
        "state": {
          "cached_elements": 16512,
          "cached_frames": 30,
          "input_sites": 3072,
          "spatial_sites": 256
        },
        "unexplained_instructions_per_call": 12802695.000000004,
        "unexplained_share": 0.5778714859268566
      },
      {
        "calls": 6,
        "instructions_per_call": 19086993.833333332,
        "state": {
          "cached_elements": 0,
          "cached_frames": 0,
          "input_sites": 3072,
          "spatial_sites": 1024
        },
        "unexplained_instructions_per_call": 10397753.666666666,
        "unexplained_share": 0.5447559609155495
      },
      {
        "calls": 3,
        "instructions_per_call": 42054468.333333336,
        "state": {
          "cached_elements": 33792,
          "cached_frames": 16,
          "input_sites": 12288,
          "spatial_sites": 1024
        },
        "unexplained_instructions_per_call": 22885014.0,
        "unexplained_share": 0.5441755634290307
      },
      {
        "calls": 3,
        "instructions_per_call": 30017406.0,
        "state": {
          "cached_elements": 0,
          "cached_frames": 0,
          "input_sites": 6912,
          "spatial_sites": 2304
        },
        "unexplained_instructions_per_call": 16939942.66666667,
        "unexplained_share": 0.564337327038408
      },
      {
        "calls": 3,
        "instructions_per_call": 76005104.0,
        "state": {
          "cached_elements": 76032,
          "cached_frames": 16,
          "input_sites": 27648,
          "spatial_sites": 2304
        },
        "unexplained_instructions_per_call": 40468889.33333334,
        "unexplained_share": 0.5324496277688581
      },
      {
        "calls": 3,
        "instructions_per_call": 74951738.66666667,
        "state": {
          "cached_elements": 148608,
          "cached_frames": 30,
          "input_sites": 27648,
          "spatial_sites": 2304
        },
        "unexplained_instructions_per_call": 39438906.33333335,
        "unexplained_share": 0.5261906799618117
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 58.51451850931816,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 58.51451850931816,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}