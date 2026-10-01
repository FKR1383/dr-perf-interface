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
    "hypothesis": "Loaded-module cardinality was constant. Model-local initialization may explain the elevated first prompt and repeated-state variability, so this candidate tests entry-state cardinality on the encoder and its stack.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "batch_size",
        "name": "batch_size",
        "rationale": "Captures per-prompt tokenizer overhead."
      },
      {
        "expression": "batch_size * max_sequence_length",
        "name": "padded_tokens",
        "rationale": "Tracks linear encoder processing."
      },
      {
        "expression": "sum((len(text) for text in prompt))",
        "name": "prompt_characters",
        "rationale": "Approximates tokenizer work and separates prompts with equal tensor dimensions."
      },
      {
        "expression": "len(self.text_encoder.__dict__) + len(self.text_encoder.encoder.__dict__)",
        "name": "encoder_state_size",
        "rationale": "Cheap cardinality of model runtime state may distinguish lazy per-instance initialization that loaded-module cardinality did not capture."
      }
    ]
  },
  "case_id": "wan-033",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-033",
    "distinct_states": 11,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "batch_size": 80745.7244771174,
        "encoder_state_size": 0.0,
        "padded_tokens": 2512.256696003312,
        "prompt_characters": 4.767695174984469
      },
      "constant": 2609659.8326468896,
      "dependent_columns": [
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 28.086393176112324,
    "max_unexplained_share": 0.1945057052025854,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "padded_tokens",
      "prompt_characters",
      "encoder_state_size"
    ],
    "raw_files": [
      "run.1586820.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3079654.0,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 8,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 376574.8333333334,
        "unexplained_share": 0.12227829273461674
      },
      {
        "calls": 3,
        "instructions_per_call": 3391845.6666666665,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 8,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 659733.3333333334,
        "unexplained_share": 0.1945057052025854
      },
      {
        "calls": 3,
        "instructions_per_call": 3083590.3333333335,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 8,
          "prompt_characters": 14
        },
        "unexplained_instructions_per_call": 378852.66666666674,
        "unexplained_share": 0.12286089451354922
      },
      {
        "calls": 3,
        "instructions_per_call": 3174220.0,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 12,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 457629.33333333326,
        "unexplained_share": 0.14417064139641653
      },
      {
        "calls": 3,
        "instructions_per_call": 3173785.6666666665,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 12,
          "prompt_characters": 13
        },
        "unexplained_instructions_per_call": 456467.3333333332,
        "unexplained_share": 0.14382424690094067
      },
      {
        "calls": 3,
        "instructions_per_call": 3156548.6666666665,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 16,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 429169.0,
        "unexplained_share": 0.1359614709990215
      },
      {
        "calls": 3,
        "instructions_per_call": 3158399.3333333335,
        "state": {
          "batch_size": 1,
          "encoder_state_size": 70,
          "padded_tokens": 16,
          "prompt_characters": 21
        },
        "unexplained_instructions_per_call": 430608.00000000006,
        "unexplained_share": 0.13633741479597578
      },
      {
        "calls": 3,
        "instructions_per_call": 3298725.3333333335,
        "state": {
          "batch_size": 2,
          "encoder_state_size": 70,
          "padded_tokens": 16,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 484185.6666666666,
        "unexplained_share": 0.1467796247762772
      },
      {
        "calls": 3,
        "instructions_per_call": 3260327.0,
        "state": {
          "batch_size": 2,
          "encoder_state_size": 70,
          "padded_tokens": 16,
          "prompt_characters": 17
        },
        "unexplained_instructions_per_call": 445159.33333333343,
        "unexplained_share": 0.1365382470326852
      },
      {
        "calls": 3,
        "instructions_per_call": 3344297.6666666665,
        "state": {
          "batch_size": 2,
          "encoder_state_size": 70,
          "padded_tokens": 32,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 494137.99999999994,
        "unexplained_share": 0.1477553882015885
      },
      {
        "calls": 3,
        "instructions_per_call": 3347722.3333333335,
        "state": {
          "batch_size": 2,
          "encoder_state_size": 70,
          "padded_tokens": 32,
          "prompt_characters": 24
        },
        "unexplained_instructions_per_call": 496401.33333333343,
        "unexplained_share": 0.14828031834977953
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 19.45057052025854,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 19.45057052025854,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de"
  }
}