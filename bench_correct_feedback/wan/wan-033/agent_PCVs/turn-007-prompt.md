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

This is iteration 6. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Source-cache cardinality may distinguish cache-warming regimes that module count and encoder attribute count could not separate.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "batch_size",
        "name": "batch_size",
        "rationale": "Captures per-prompt tokenizer and encoder overhead."
      },
      {
        "expression": "batch_size * max_sequence_length",
        "name": "padded_tokens",
        "rationale": "Tracks linear tensor-processing work."
      },
      {
        "expression": "sum((len(text) for text in prompt))",
        "name": "prompt_characters",
        "rationale": "Approximates tokenizer input work and distinguishes equal-shape prompts."
      },
      {
        "expression": "len(__import__('sys').modules['linecache'].cache) if 'linecache' in __import__('sys').modules else 0",
        "name": "source_cache_entries",
        "rationale": "Reads existing runtime cache cardinality without importing linecache or accessing files."
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
        "batch_size": 80617.43035134947,
        "padded_tokens": 2459.596877890521,
        "prompt_characters": 4.382356595568442,
        "source_cache_entries": 0.0
      },
      "constant": 2613972.684816295,
      "dependent_columns": [
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 28.047471481841058,
    "max_unexplained_share": 0.19320960226490774,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "padded_tokens",
      "prompt_characters",
      "source_cache_entries"
    ],
    "raw_files": [
      "run.1587525.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3076939.6666666665,
        "state": {
          "batch_size": 1,
          "padded_tokens": 8,
          "prompt_characters": 4,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 370104.1666666665,
        "unexplained_share": 0.12028320563971621
      },
      {
        "calls": 3,
        "instructions_per_call": 3390866.6666666665,
        "state": {
          "batch_size": 1,
          "padded_tokens": 8,
          "prompt_characters": 8,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 655148.0000000001,
        "unexplained_share": 0.19320960226490774
      },
      {
        "calls": 3,
        "instructions_per_call": 3082288.0,
        "state": {
          "batch_size": 1,
          "padded_tokens": 8,
          "prompt_characters": 14,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 373411.6666666668,
        "unexplained_share": 0.12114755878317238
      },
      {
        "calls": 3,
        "instructions_per_call": 3175246.3333333335,
        "state": {
          "batch_size": 1,
          "padded_tokens": 12,
          "prompt_characters": 4,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 455412.00000000006,
        "unexplained_share": 0.14342572266571654
      },
      {
        "calls": 3,
        "instructions_per_call": 3179018.0,
        "state": {
          "batch_size": 1,
          "padded_tokens": 12,
          "prompt_characters": 13,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 457625.9999999998,
        "unexplained_share": 0.14395200027178198
      },
      {
        "calls": 3,
        "instructions_per_call": 3156664.6666666665,
        "state": {
          "batch_size": 1,
          "padded_tokens": 16,
          "prompt_characters": 4,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 426870.6666666668,
        "unexplained_share": 0.13522838557236683
      },
      {
        "calls": 3,
        "instructions_per_call": 3161780.0,
        "state": {
          "batch_size": 1,
          "padded_tokens": 16,
          "prompt_characters": 21,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 430470.6666666667,
        "unexplained_share": 0.1361482034381477
      },
      {
        "calls": 3,
        "instructions_per_call": 3301857.3333333335,
        "state": {
          "batch_size": 2,
          "padded_tokens": 16,
          "prompt_characters": 8,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 483257.33333333355,
        "unexplained_share": 0.14635924104130488
      },
      {
        "calls": 3,
        "instructions_per_call": 3259651.6666666665,
        "state": {
          "batch_size": 2,
          "padded_tokens": 16,
          "prompt_characters": 17,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 441381.3333333333,
        "unexplained_share": 0.1354075154247054
      },
      {
        "calls": 3,
        "instructions_per_call": 3344078.6666666665,
        "state": {
          "batch_size": 2,
          "padded_tokens": 32,
          "prompt_characters": 8,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 491840.99999999994,
        "unexplained_share": 0.14707817878287552
      },
      {
        "calls": 3,
        "instructions_per_call": 3348016.6666666665,
        "state": {
          "batch_size": 2,
          "padded_tokens": 32,
          "prompt_characters": 24,
          "source_cache_entries": 45
        },
        "unexplained_instructions_per_call": 494487.0000000001,
        "unexplained_share": 0.14769550131669998
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 19.320960226490776,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 19.320960226490776,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a9b5db5abd9f157a11666922e5bfb352229008463251da0d1d8b6d9004cad2de"
  }
}