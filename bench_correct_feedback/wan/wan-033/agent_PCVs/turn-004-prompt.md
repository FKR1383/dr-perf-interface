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

This is iteration 4. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The substantial unexplained work across repeated identical input states suggests runtime initialization contributes beyond tensor dimensions. Loaded-module cardinality may distinguish initialization regimes, including the unusually costly red-kite state.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "batch_size",
        "name": "batch_size",
        "rationale": "Captures per-prompt tokenizer and encoder overhead."
      },
      {
        "expression": "batch_size * max_sequence_length",
        "name": "padded_tokens",
        "rationale": "Tracks encoder tensor-processing volume."
      },
      {
        "expression": "sum((len(text) for text in prompt))",
        "name": "prompt_characters",
        "rationale": "Approximates tokenizer input work and distinguishes prompts with identical padded shapes."
      },
      {
        "expression": "len(__import__('sys').modules)",
        "name": "loaded_modules",
        "rationale": "Cheap runtime entry state that can distinguish library initialization regimes involving lazy imports."
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
        "batch_size": 80368.67788361979,
        "loaded_modules": 0.0,
        "padded_tokens": 2560.6766597639253,
        "prompt_characters": -3.108025125975013
      },
      "constant": 2606503.355403092,
      "dependent_columns": [
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 28.055436509661376,
    "max_unexplained_share": 0.19626976025076662,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "padded_tokens",
      "prompt_characters",
      "loaded_modules"
    ],
    "raw_files": [
      "run.1586277.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3079072.3333333335,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 8,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 379139.66666666674,
        "unexplained_share": 0.12313438127522609
      },
      {
        "calls": 3,
        "instructions_per_call": 3395242.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 8,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 666383.3333333334,
        "unexplained_share": 0.19626976025076662
      },
      {
        "calls": 3,
        "instructions_per_call": 3081895.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 8,
          "prompt_characters": 14
        },
        "unexplained_instructions_per_call": 380745.3333333334,
        "unexplained_share": 0.12354260392821084
      },
      {
        "calls": 3,
        "instructions_per_call": 3175090.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 12,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 461987.6666666669,
        "unexplained_share": 0.1455038019919646
      },
      {
        "calls": 3,
        "instructions_per_call": 3176433.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 12,
          "prompt_characters": 13
        },
        "unexplained_instructions_per_call": 462400.9999999998,
        "unexplained_share": 0.14557240779201067
      },
      {
        "calls": 3,
        "instructions_per_call": 3165606.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 16,
          "prompt_characters": 4
        },
        "unexplained_instructions_per_call": 440864.9999999998,
        "unexplained_share": 0.139267173489057
      },
      {
        "calls": 3,
        "instructions_per_call": 3168212.6666666665,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "padded_tokens": 16,
          "prompt_characters": 21
        },
        "unexplained_instructions_per_call": 442550.00000000023,
        "unexplained_share": 0.1396844361668483
      },
      {
        "calls": 3,
        "instructions_per_call": 3302497.6666666665,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "padded_tokens": 16,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 490551.0000000001,
        "unexplained_share": 0.14853939336621286
      },
      {
        "calls": 3,
        "instructions_per_call": 3264080.6666666665,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "padded_tokens": 16,
          "prompt_characters": 17
        },
        "unexplained_instructions_per_call": 451743.00000000023,
        "unexplained_share": 0.13839823403057244
      },
      {
        "calls": 3,
        "instructions_per_call": 3352327.6666666665,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "padded_tokens": 32,
          "prompt_characters": 8
        },
        "unexplained_instructions_per_call": 504851.33333333355,
        "unexplained_share": 0.15059725168074767
      },
      {
        "calls": 3,
        "instructions_per_call": 3352376.0,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "padded_tokens": 32,
          "prompt_characters": 24
        },
        "unexplained_instructions_per_call": 504258.00000000006,
        "unexplained_share": 0.15041809152672614
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 19.62697602507666,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 19.62697602507666,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de"
  }
}