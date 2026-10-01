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
    "hypothesis": "The higher instruction count at 27 tokens than at 32 suggests CPU kernel alignment costs. Combining attention interactions frees a feature to capture token tile remainders and may reduce the previous 10.61% irregularity.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "hidden_states.numel()",
        "name": "hidden_elements",
        "rationale": "Captures tokenwise projections, normalization, modulation, and feed-forward work."
      },
      {
        "expression": "encoder_hidden_states.numel()",
        "name": "encoder_elements",
        "rationale": "Captures conditioning key/value projections and normalization."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * (hidden_states.shape[1] + encoder_hidden_states.shape[1]) * hidden_states.shape[2]",
        "name": "attention_work",
        "rationale": "Combines self-attention and cross-attention interaction work."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] % 16)",
        "name": "token_tile_remainder",
        "rationale": "Models CPU kernel remainder handling that can make unaligned token counts more expensive than nearby aligned counts."
      }
    ]
  },
  "case_id": "wan-024",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 18,
    "case": "wan-024",
    "distinct_states": 6,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "attention_work": 2.060225238838898,
        "encoder_elements": -6.666910280898547,
        "hidden_elements": 175.67133308298298,
        "token_tile_remainder": 459.3220514340665
      },
      "constant": 2267947.4228357133,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 21.27815550705418,
    "max_unexplained_share": 0.10090402949748473,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "hidden_elements",
      "encoder_elements",
      "attention_work",
      "token_tile_remainder"
    ],
    "raw_files": [
      "run.1573113.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 2459034.0,
        "state": {
          "attention_work": 3744,
          "encoder_elements": 128,
          "hidden_elements": 288,
          "token_tile_remainder": 9
        },
        "unexplained_instructions_per_call": 112476.66666666664,
        "unexplained_share": 0.045740183611396444
      },
      {
        "calls": 3,
        "instructions_per_call": 2479759.6666666665,
        "state": {
          "attention_work": 11264,
          "encoder_elements": 192,
          "hidden_elements": 512,
          "token_tile_remainder": 0
        },
        "unexplained_instructions_per_call": 110737.33333333334,
        "unexplained_share": 0.0446564781345074
      },
      {
        "calls": 3,
        "instructions_per_call": 2549240.3333333335,
        "state": {
          "attention_work": 15552,
          "encoder_elements": 288,
          "hidden_elements": 576,
          "token_tile_remainder": 2
        },
        "unexplained_instructions_per_call": 152612.66666666666,
        "unexplained_share": 0.05986593914710015
      },
      {
        "calls": 3,
        "instructions_per_call": 2737577.6666666665,
        "state": {
          "attention_work": 28512,
          "encoder_elements": 192,
          "hidden_elements": 864,
          "token_tile_remainder": 11
        },
        "unexplained_instructions_per_call": 250074.33333333334,
        "unexplained_share": 0.09134876295138294
      },
      {
        "calls": 3,
        "instructions_per_call": 2686239.6666666665,
        "state": {
          "attention_work": 36864,
          "encoder_elements": 128,
          "hidden_elements": 1024,
          "token_tile_remainder": 0
        },
        "unexplained_instructions_per_call": 160705.33333333334,
        "unexplained_share": 0.059825389122018034
      },
      {
        "calls": 3,
        "instructions_per_call": 3009341.3333333335,
        "state": {
          "attention_work": 87552,
          "encoder_elements": 288,
          "hidden_elements": 1536,
          "token_tile_remainder": 0
        },
        "unexplained_instructions_per_call": 303654.6666666667,
        "unexplained_share": 0.10090402949748473
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "9e9db6b65c85c9f5e43f7675aa549ef9f2429cf8375c73fd3ac84f6265d51ffe",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 10.090402949748473,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 10.090402949748473,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "9e9db6b65c85c9f5e43f7675aa549ef9f2429cf8375c73fd3ac84f6265d51ffe"
  }
}