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
    "hypothesis": "The previous shape model leaves substantial unexplained work at every state. Runtime initialization may distinguish repetitions of identical shapes; loaded-module cardinality tests this while retaining the main computational scaling terms.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[2] // self.config.patch_size[0]) * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2])",
        "name": "video_tokens",
        "rationale": "Tracks linear video processing for the fixed model."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[2] // self.config.patch_size[0] * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2])) ** 2",
        "name": "self_attention_pairs",
        "rationale": "Tracks quadratic self-attention work."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[2] // self.config.patch_size[0]) * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2]) * encoder_hidden_states.shape[1]",
        "name": "cross_attention_pairs",
        "rationale": "Tracks attention work involving the variable text context."
      },
      {
        "expression": "len(__import__('sys').modules)",
        "name": "loaded_modules",
        "rationale": "Cheap cardinality of existing runtime state that may distinguish lazy initialization from warmed execution across repeated shapes."
      }
    ]
  },
  "case_id": "wan-023",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 18,
    "case": "wan-023",
    "distinct_states": 6,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "cross_attention_pairs": -101.83704020342317,
        "loaded_modules": 0.0,
        "self_attention_pairs": 148.822107334381,
        "video_tokens": 1677.1922218217626
      },
      "constant": 3685580.8717504954,
      "dependent_columns": [
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 24.972883617971092,
    "max_unexplained_share": 0.15617066495321094,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "video_tokens",
      "self_attention_pairs",
      "cross_attention_pairs",
      "loaded_modules"
    ],
    "raw_files": [
      "run.1571626.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 4083412.6666666665,
        "state": {
          "cross_attention_pairs": 36,
          "loaded_modules": 3495,
          "self_attention_pairs": 81,
          "video_tokens": 9
        },
        "unexplained_instructions_per_call": 358679.33333333343,
        "unexplained_share": 0.08783813016530784
      },
      {
        "calls": 3,
        "instructions_per_call": 4050250.3333333335,
        "state": {
          "cross_attention_pairs": 96,
          "loaded_modules": 3495,
          "self_attention_pairs": 256,
          "video_tokens": 16
        },
        "unexplained_instructions_per_call": 330237.6666666667,
        "unexplained_share": 0.0815351248659445
      },
      {
        "calls": 3,
        "instructions_per_call": 4182669.0,
        "state": {
          "cross_attention_pairs": 162,
          "loaded_modules": 3495,
          "self_attention_pairs": 324,
          "video_tokens": 18
        },
        "unexplained_instructions_per_call": 432137.3333333333,
        "unexplained_share": 0.10331616805760468
      },
      {
        "calls": 3,
        "instructions_per_call": 4446134.666666667,
        "state": {
          "cross_attention_pairs": 162,
          "loaded_modules": 3495,
          "self_attention_pairs": 729,
          "video_tokens": 27
        },
        "unexplained_instructions_per_call": 610355.6666666666,
        "unexplained_share": 0.13727781824572113
      },
      {
        "calls": 3,
        "instructions_per_call": 4370080.0,
        "state": {
          "cross_attention_pairs": 128,
          "loaded_modules": 3495,
          "self_attention_pairs": 1024,
          "video_tokens": 32
        },
        "unexplained_instructions_per_call": 496243.0,
        "unexplained_share": 0.11355467176802256
      },
      {
        "calls": 3,
        "instructions_per_call": 4810032.666666667,
        "state": {
          "cross_attention_pairs": 432,
          "loaded_modules": 3495,
          "self_attention_pairs": 2304,
          "video_tokens": 48
        },
        "unexplained_instructions_per_call": 751185.9999999998,
        "unexplained_share": 0.15617066495321094
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "12f7610a1b27e9e14262b3a170984e9b3395299b9cf48cd248beac0e979d56ba",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 15.617066495321094,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 15.617066495321094,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "12f7610a1b27e9e14262b3a170984e9b3395299b9cf48cd248beac0e979d56ba"
  }
}