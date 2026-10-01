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
    "hypothesis": "Adding prompt character count separates enough entry states for validation while retaining the dominant batch and sequence-size predictors. The previous measurements suggest shape-dependent variation is small relative to fixed encoder overhead.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "batch_size",
        "name": "batch_size",
        "rationale": "Captures per-prompt tokenizer and encoder overhead."
      },
      {
        "expression": "batch_size * max_sequence_length",
        "name": "padded_tokens",
        "rationale": "Tracks linear tensor processing."
      },
      {
        "expression": "batch_size * max_sequence_length ** 2",
        "name": "attention_elements",
        "rationale": "Tracks quadratic attention processing."
      },
      {
        "expression": "sum((len(text) for text in prompt))",
        "name": "prompt_characters",
        "rationale": "Cheap string lengths approximate tokenizer input processing and distinguish prompts sharing the same padded tensor shape."
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
        "attention_elements": -1493.5621809972954,
        "batch_size": -114080.45170789174,
        "padded_tokens": 39702.43348940045,
        "prompt_characters": 5.47725166862976
      },
      "constant": 2645196.918204593,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 28.14301764126867,
    "max_unexplained_share": 0.18343258652438738,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "padded_tokens",
      "attention_elements",
      "prompt_characters"
    ],
    "raw_files": [
      "run.1585790.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3076882.5,
        "state": {
          "attention_elements": 64,
          "batch_size": 1,
          "padded_tokens": 8,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 340605.83333333355,
        "unexplained_share": 0.11069835566789878
      },
      {
        "calls": 3,
        "instructions_per_call": 3388640.0,
        "state": {
          "attention_elements": 64,
          "batch_size": 1,
          "padded_tokens": 8,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 621587.0,
        "unexplained_share": 0.18343258652438738
      },
      {
        "calls": 3,
        "instructions_per_call": 3080428.6666666665,
        "state": {
          "attention_elements": 64,
          "batch_size": 1,
          "padded_tokens": 8,
          "prompt_characters": 14
        },
        "unexplained_instructions_per_call": 342600.9999999998,
        "unexplained_share": 0.11121861178195323
      },
      {
        "calls": 3,
        "instructions_per_call": 3172368.3333333335,
        "state": {
          "attention_elements": 144,
          "batch_size": 1,
          "padded_tokens": 12,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 388189.99999999994,
        "unexplained_share": 0.1223659925996403
      },
      {
        "calls": 3,
        "instructions_per_call": 3170699.0,
        "state": {
          "attention_elements": 144,
          "batch_size": 1,
          "padded_tokens": 12,
          "prompt_characters": 13
        },
        "unexplained_instructions_per_call": 386115.6666666668,
        "unexplained_share": 0.12177619719395212
      },
      {
        "calls": 3,
        "instructions_per_call": 3149823.0,
        "state": {
          "attention_elements": 256,
          "batch_size": 1,
          "padded_tokens": 16,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 375850.00000000023,
        "unexplained_share": 0.11932416519912396
      },
      {
        "calls": 3,
        "instructions_per_call": 3158489.3333333335,
        "state": {
          "attention_elements": 256,
          "batch_size": 1,
          "padded_tokens": 16,
          "prompt_characters": 21
        },
        "unexplained_instructions_per_call": 382044.6666666666,
        "unexplained_share": 0.12095803605689975
      },
      {
        "calls": 3,
        "instructions_per_call": 3300797.6666666665,
        "state": {
          "attention_elements": 128,
          "batch_size": 2,
          "padded_tokens": 16,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 427175.99999999965,
        "unexplained_share": 0.1294159906600353
      },
      {
        "calls": 3,
        "instructions_per_call": 3258352.0,
        "state": {
          "attention_elements": 128,
          "batch_size": 2,
          "padded_tokens": 16,
          "prompt_characters": 17
        },
        "unexplained_instructions_per_call": 385039.0,
        "unexplained_share": 0.11816986010105722
      },
      {
        "calls": 3,
        "instructions_per_call": 3339696.0,
        "state": {
          "attention_elements": 512,
          "batch_size": 2,
          "padded_tokens": 32,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 403302.3333333335,
        "unexplained_share": 0.1207601929437091
      },
      {
        "calls": 3,
        "instructions_per_call": 3341908.6666666665,
        "state": {
          "attention_elements": 512,
          "batch_size": 2,
          "padded_tokens": 32,
          "prompt_characters": 24
        },
        "unexplained_instructions_per_call": 404674.6666666667,
        "unexplained_share": 0.121090881598001
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 18.343258652438738,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 18.343258652438738,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de"
  }
}