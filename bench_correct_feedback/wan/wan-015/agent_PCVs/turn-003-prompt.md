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

This is iteration 3. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The state means are approximately linear in spatial area and temporal volume. Large unexplained variation within those states may reflect differing input-view layouts; channel stride exposes that entry-state distinction.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[3] * x.shape[4]",
        "name": "spatial_sites",
        "rationale": "Models spatial convolution, normalization, padding, and cache-copy work."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "input_sites",
        "rationale": "Models work proportional to the temporal chunk volume."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "warm_cache",
        "rationale": "Models the additional operations performed with populated convolution caches."
      },
      {
        "expression": "x.stride(1)",
        "name": "channel_stride",
        "rationale": "Distinguishes input views with identical shapes but different channel strides, exposing layout variation hidden by the previous state grouping."
      }
    ]
  },
  "case_id": "wan-015",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-015",
    "distinct_states": 10,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "channel_stride": 0.363475942140158,
        "input_sites": 3620.2275914585443,
        "spatial_sites": 265.9558857605961,
        "warm_cache": 3389027.899283675
      },
      "constant": 9188117.704736536,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 40.17189541272819,
    "max_unexplained_share": 0.3894279022713213,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "spatial_sites",
      "input_sites",
      "warm_cache",
      "channel_stride"
    ],
    "raw_files": [
      "run.1552734.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 12975411.0,
        "state": {
          "channel_stride": 256,
          "input_sites": 256,
          "spatial_sites": 256,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 2932921.666666664,
        "unexplained_share": 0.2260368990752327
      },
      {
        "calls": 3,
        "instructions_per_call": 12863347.0,
        "state": {
          "channel_stride": 1280,
          "input_sites": 256,
          "spatial_sites": 256,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 2848782.666666667,
        "unexplained_share": 0.22146511842265212
      },
      {
        "calls": 3,
        "instructions_per_call": 12844189.666666666,
        "state": {
          "channel_stride": 2304,
          "input_sites": 256,
          "spatial_sites": 256,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 2830226.333333333,
        "unexplained_share": 0.2203507116278699
      },
      {
        "calls": 3,
        "instructions_per_call": 23142108.333333332,
        "state": {
          "channel_stride": 1280,
          "input_sites": 1024,
          "spatial_sites": 256,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 6752152.333333334,
        "unexplained_share": 0.29176910919597143
      },
      {
        "calls": 6,
        "instructions_per_call": 22220307.5,
        "state": {
          "channel_stride": 2304,
          "input_sites": 1024,
          "spatial_sites": 256,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 5925055.833333333,
        "unexplained_share": 0.2666504877726527
      },
      {
        "calls": 3,
        "instructions_per_call": 19087480.666666668,
        "state": {
          "channel_stride": 1024,
          "input_sites": 1024,
          "spatial_sites": 1024,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 5973614.000000002,
        "unexplained_share": 0.3129597930874133
      },
      {
        "calls": 3,
        "instructions_per_call": 19092275.666666668,
        "state": {
          "channel_stride": 5120,
          "input_sites": 1024,
          "spatial_sites": 1024,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 5973860.333333334,
        "unexplained_share": 0.3128940958967577
      },
      {
        "calls": 3,
        "instructions_per_call": 42197288.333333336,
        "state": {
          "channel_stride": 5120,
          "input_sites": 4096,
          "spatial_sites": 1024,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 14424527.666666653,
        "unexplained_share": 0.341835417307423
      },
      {
        "calls": 3,
        "instructions_per_call": 30024404.0,
        "state": {
          "channel_stride": 20736,
          "input_sites": 2304,
          "spatial_sites": 2304,
          "warm_cache": 0
        },
        "unexplained_instructions_per_call": 11692340.666666668,
        "unexplained_share": 0.3894279022713213
      },
      {
        "calls": 6,
        "instructions_per_call": 75620289.16666667,
        "state": {
          "channel_stride": 20736,
          "input_sites": 9216,
          "spatial_sites": 2304,
          "warm_cache": 1
        },
        "unexplained_instructions_per_call": 28729238.666666653,
        "unexplained_share": 0.37991442486218985
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 38.94279022713213,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 38.94279022713213,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "133a62d4e4508720f10ab2bd19a05c8f0fbceeb046cf23196a9867b8656cc261"
  }
}