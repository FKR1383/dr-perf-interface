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
    "hypothesis": "With model dimensions and layer count fixed, instruction count should follow constant overhead plus linear video and text processing, quadratic self-attention, and video-by-text cross-attention.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[2] // self.config.patch_size[0]) * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2])",
        "name": "video_tokens",
        "rationale": "Tracks patch embedding, projections, normalization, feed-forward operations, and output reconstruction for the fixed model."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[2] // self.config.patch_size[0] * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2])) ** 2",
        "name": "self_attention_pairs",
        "rationale": "Tracks quadratic self-attention work."
      },
      {
        "expression": "encoder_hidden_states.shape[0] * encoder_hidden_states.shape[1]",
        "name": "text_tokens",
        "rationale": "Tracks text embedding and cross-attention key/value projections."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[2] // self.config.patch_size[0]) * (hidden_states.shape[3] // self.config.patch_size[1]) * (hidden_states.shape[4] // self.config.patch_size[2]) * encoder_hidden_states.shape[1]",
        "name": "cross_attention_pairs",
        "rationale": "Tracks cross-attention work over video queries and text keys."
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
        "cross_attention_pairs": 367.25172658643567,
        "self_attention_pairs": 51.131342998863985,
        "text_tokens": -7581.779648056417,
        "video_tokens": 3436.3167080090147
      },
      "constant": 3705461.7816573596,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 25.023664445616305,
    "max_unexplained_share": 0.14992625431213302,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "video_tokens",
      "self_attention_pairs",
      "text_tokens",
      "cross_attention_pairs"
    ],
    "raw_files": [
      "run.1571159.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 4084964.3333333335,
        "state": {
          "cross_attention_pairs": 36,
          "self_attention_pairs": 81,
          "text_tokens": 4,
          "video_tokens": 9
        },
        "unexplained_instructions_per_call": 346176.6666666668,
        "unexplained_share": 0.08474410996489323
      },
      {
        "calls": 3,
        "instructions_per_call": 4047741.0,
        "state": {
          "cross_attention_pairs": 96,
          "self_attention_pairs": 256,
          "text_tokens": 6,
          "video_tokens": 16
        },
        "unexplained_instructions_per_call": 310822.33333333326,
        "unexplained_share": 0.0767890863899971
      },
      {
        "calls": 3,
        "instructions_per_call": 4179381.0,
        "state": {
          "cross_attention_pairs": 162,
          "self_attention_pairs": 324,
          "text_tokens": 9,
          "video_tokens": 18
        },
        "unexplained_instructions_per_call": 409347.3333333333,
        "unexplained_share": 0.09794448827071121
      },
      {
        "calls": 3,
        "instructions_per_call": 4440294.0,
        "state": {
          "cross_attention_pairs": 162,
          "self_attention_pairs": 729,
          "text_tokens": 6,
          "video_tokens": 27
        },
        "unexplained_instructions_per_call": 583588.3333333333,
        "unexplained_share": 0.13143011100916588
      },
      {
        "calls": 3,
        "instructions_per_call": 4367829.333333333,
        "state": {
          "cross_attention_pairs": 128,
          "self_attention_pairs": 1024,
          "text_tokens": 4,
          "video_tokens": 32
        },
        "unexplained_instructions_per_call": 476007.3333333333,
        "unexplained_share": 0.10898029593341865
      },
      {
        "calls": 3,
        "instructions_per_call": 4799828.666666667,
        "state": {
          "cross_attention_pairs": 432,
          "self_attention_pairs": 2304,
          "text_tokens": 9,
          "video_tokens": 48
        },
        "unexplained_instructions_per_call": 719620.3333333331,
        "unexplained_share": 0.14992625431213302
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "12f7610a1b27e9e14262b3a170984e9b3395299b9cf48cd248beac0e979d56ba",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 14.992625431213302,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 14.992625431213302,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "12f7610a1b27e9e14262b3a170984e9b3395299b9cf48cd248beac0e979d56ba"
  }
}