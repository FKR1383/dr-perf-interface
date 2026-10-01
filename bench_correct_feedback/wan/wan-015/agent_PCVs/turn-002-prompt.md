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
    "hypothesis": "Instruction count is explained by spatial work, temporal-volume work, bottleneck attention pairs, and the fixed overhead of processing a populated feature cache.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4]",
        "name": "spatial_sites",
        "rationale": "Captures spatial convolution, padding, normalization, and cached-frame copying costs."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "input_sites",
        "rationale": "Captures convolution and elementwise work that scales with the input chunk's temporal length."
      },
      {
        "expression": "x.shape[0] * (x.shape[3] // 8) ** 2 * (x.shape[4] // 8) ** 2",
        "name": "attention_pairs",
        "rationale": "Captures quadratic spatial attention work at the encoder bottleneck, which has one temporal frame in this workload."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "warm_cache",
        "rationale": "Distinguishes initial chunks from subsequent chunks with cached concatenations and temporal downsampling."
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
        "attention_pairs": 994.2743634259303,
        "input_sites": 4171.038196658872,
        "spatial_sites": -88.84386026004539,
        "warm_cache": 3757146.9285714226
      },
      "constant": 10334848.84354062,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 39.34647286776453,
    "max_unexplained_share": 0.28749205918488674,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "spatial_sites",
      "input_sites",
      "attention_pairs",
      "warm_cache"
    ],
    "raw_files": [
      "run.1552075.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 9,
        "instructions_per_call": 12886785.888888888,
        "state": {
          "attention_pairs": 16,
          "input_sites": 256,
          "spatial_sites": 256,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 1847510.2222222222,
        "unexplained_share": 0.1433647022734477
      },
      {
        "calls": 9,
        "instructions_per_call": 22422185.555555556,
        "state": {
          "attention_pairs": 16,
          "input_sites": 1024,
          "spatial_sites": 256,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 4333175.444444441,
        "unexplained_share": 0.19325392851237055
      },
      {
        "calls": 6,
        "instructions_per_call": 19079706.0,
        "state": {
          "attention_pairs": 256,
          "input_sites": 1024,
          "spatial_sites": 1024,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 4445745.333333334,
        "unexplained_share": 0.23300911100691665
      },
      {
        "calls": 3,
        "instructions_per_call": 42075646.0,
        "state": {
          "attention_pairs": 256,
          "input_sites": 4096,
          "spatial_sites": 1024,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 10789936.999999996,
        "unexplained_share": 0.2564413865446058
      },
      {
        "calls": 3,
        "instructions_per_call": 30012662.0,
        "state": {
          "attention_pairs": 1296,
          "input_sites": 2304,
          "spatial_sites": 2304,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 8628402.000000002,
        "unexplained_share": 0.28749205918488674
      },
      {
        "calls": 6,
        "instructions_per_call": 75501966.5,
        "state": {
          "attention_pairs": 1296,
          "input_sites": 9216,
          "spatial_sites": 2304,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 21427431.999999985,
        "unexplained_share": 0.2837996544103257
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 28.749205918488673,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 28.749205918488673,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}