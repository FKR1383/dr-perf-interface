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
    "hypothesis": "With two encoder calls per invocation and fixed model dimensions, instruction count is primarily explained by per-prompt overhead, padded token volume, batched attention size, and shared relative-position work.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "1 if isinstance(prompt, str) else len(prompt)",
        "name": "batch_size",
        "rationale": "Captures per-prompt cleaning, tokenization, slicing, and padding overhead."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length",
        "name": "padded_tokens",
        "rationale": "Models encoder projections, feed-forward computation, and embedding copies."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length ** 2",
        "name": "attention_elements",
        "rationale": "Models quadratic attention computation across the batch."
      },
      {
        "expression": "max_sequence_length ** 2",
        "name": "position_pairs",
        "rationale": "Captures relative-position bias construction shared across batch elements."
      }
    ]
  },
  "case_id": "wan-035",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 18,
    "case": "wan-035",
    "distinct_states": 5,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 5; need 6"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 26.90033721923828,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "padded_tokens",
      "attention_elements",
      "position_pairs"
    ],
    "raw_files": [
      "run.1589567.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 16346707.166666666,
        "state": {
          "attention_elements": 64,
          "batch_size": 1,
          "padded_tokens": 8,
          "position_pairs": 64
        }
      },
      {
        "calls": 3,
        "instructions_per_call": 16289492.666666666,
        "state": {
          "attention_elements": 144,
          "batch_size": 1,
          "padded_tokens": 12,
          "position_pairs": 144
        }
      },
      {
        "calls": 3,
        "instructions_per_call": 16252642.666666666,
        "state": {
          "attention_elements": 256,
          "batch_size": 1,
          "padded_tokens": 16,
          "position_pairs": 256
        }
      },
      {
        "calls": 3,
        "instructions_per_call": 16684680.666666666,
        "state": {
          "attention_elements": 128,
          "batch_size": 2,
          "padded_tokens": 16,
          "position_pairs": 64
        }
      },
      {
        "calls": 3,
        "instructions_per_call": 16818524.333333332,
        "state": {
          "attention_elements": 512,
          "batch_size": 2,
          "padded_tokens": 32,
          "position_pairs": 256
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "4feecb9cffd2264d9024147562469be33918af9922ef0218791ad864e5b41715",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 5; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "success": false,
      "threshold_percent": 10.0,
      "valid": false
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": null,
      "iteration": 1,
      "reasons": [
        "insufficient state points: 5; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "4feecb9cffd2264d9024147562469be33918af9922ef0218791ad864e5b41715"
  }
}