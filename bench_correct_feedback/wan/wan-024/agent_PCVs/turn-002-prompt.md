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
    "hypothesis": "With fixed model dimensions and execution branches, instruction count is approximately a constant overhead plus linear hidden and encoder processing and the self-attention and cross-attention interaction costs.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "hidden_states.numel()",
        "name": "hidden_elements",
        "rationale": "Captures tokenwise normalization, modulation, projections, and feed-forward work at fixed model dimensions."
      },
      {
        "expression": "encoder_hidden_states.numel()",
        "name": "encoder_elements",
        "rationale": "Captures cross-attention key/value projections and key normalization."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] ** 2 * hidden_states.shape[2]",
        "name": "self_attention_work",
        "rationale": "Captures quadratic self-attention score and value aggregation work."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * encoder_hidden_states.shape[1] * hidden_states.shape[2]",
        "name": "cross_attention_work",
        "rationale": "Captures cross-attention work proportional to video tokens times conditioning tokens."
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
        "cross_attention_work": 23.191083849024743,
        "encoder_elements": -398.4289214738898,
        "hidden_elements": 240.32228137945577,
        "self_attention_work": -2.3782144357599195
      },
      "constant": 2289111.344851879,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 21.91313276439905,
    "max_unexplained_share": 0.10614283380361253,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "hidden_elements",
      "encoder_elements",
      "self_attention_work",
      "cross_attention_work"
    ],
    "raw_files": [
      "run.1572687.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 2459135.0,
        "state": {
          "cross_attention_work": 1152,
          "encoder_elements": 128,
          "hidden_elements": 288,
          "self_attention_work": 2592
        },
        "unexplained_instructions_per_call": 119689.99999999999,
        "unexplained_share": 0.048671585740514445
      },
      {
        "calls": 3,
        "instructions_per_call": 2479673.0,
        "state": {
          "cross_attention_work": 3072,
          "encoder_elements": 192,
          "hidden_elements": 512,
          "self_attention_work": 8192
        },
        "unexplained_instructions_per_call": 107984.33333333333,
        "unexplained_share": 0.043547811882185004
      },
      {
        "calls": 3,
        "instructions_per_call": 2549109.0,
        "state": {
          "cross_attention_work": 5184,
          "encoder_elements": 288,
          "hidden_elements": 576,
          "self_attention_work": 10368
        },
        "unexplained_instructions_per_call": 148144.00000000003,
        "unexplained_share": 0.05811599268607189
      },
      {
        "calls": 3,
        "instructions_per_call": 2737485.3333333335,
        "state": {
          "cross_attention_work": 5184,
          "encoder_elements": 192,
          "hidden_elements": 864,
          "self_attention_work": 23328
        },
        "unexplained_instructions_per_call": 248563.00000000003,
        "unexplained_share": 0.09079975588301478
      },
      {
        "calls": 3,
        "instructions_per_call": 2686166.3333333335,
        "state": {
          "cross_attention_work": 4096,
          "encoder_elements": 128,
          "hidden_elements": 1024,
          "self_attention_work": 32768
        },
        "unexplained_instructions_per_call": 178537.66666666666,
        "unexplained_share": 0.06646560358200701
      },
      {
        "calls": 3,
        "instructions_per_call": 3009441.6666666665,
        "state": {
          "cross_attention_work": 13824,
          "encoder_elements": 288,
          "hidden_elements": 1536,
          "self_attention_work": 73728
        },
        "unexplained_instructions_per_call": 319430.6666666667,
        "unexplained_share": 0.10614283380361253
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "9e9db6b65c85c9f5e43f7675aa549ef9f2429cf8375c73fd3ac84f6265d51ffe",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 10.614283380361252,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 10.614283380361252,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "9e9db6b65c85c9f5e43f7675aa549ef9f2429cf8375c73fd3ac84f6265d51ffe"
  }
}