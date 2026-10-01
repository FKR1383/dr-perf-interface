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
    "hypothesis": "Regex compilation cache state may explain prompt-cleaning warmup costs that module and source-cache cardinalities did not capture.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "len(re._main._cache)",
        "name": "regex_cache_entries",
        "rationale": "Reads existing regex compilation cache cardinality to distinguish cold and warmed text processing."
      },
      {
        "expression": "1 if isinstance(prompt, str) else len(prompt)",
        "name": "batch_size",
        "rationale": "Captures per-prompt cleaning, tokenization, and embedding reconstruction overhead."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length",
        "name": "token_positions",
        "rationale": "Models encoder processing over padded sequences."
      },
      {
        "expression": "len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))",
        "name": "prompt_characters",
        "rationale": "Captures input-dependent cleaning and tokenization work."
      }
    ]
  },
  "case_id": "wan-031",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-031",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "batch_size": 169246.2789742528,
        "prompt_characters": 106.9058521433009,
        "regex_cache_entries": -846679.8430496308,
        "token_positions": 2699.6189138537975
      },
      "constant": 15576085.06253987,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 30.307602568063885,
    "max_unexplained_share": 0.12147983827317263,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "regex_cache_entries",
      "batch_size",
      "token_positions",
      "prompt_characters"
    ],
    "raw_files": [
      "run.1582496.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 4283201.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 8,
          "regex_cache_entries": 14,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 362851.0,
        "unexplained_share": 0.08471491298213649
      },
      {
        "calls": 6,
        "instructions_per_call": 3276107.6666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "regex_cache_entries": 15,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 218363.99999999997,
        "unexplained_share": 0.06665348706997114
      },
      {
        "calls": 2,
        "instructions_per_call": 3491814.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 8,
          "regex_cache_entries": 15,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 424185.0,
        "unexplained_share": 0.12147983827317263
      },
      {
        "calls": 3,
        "instructions_per_call": 3285689.3333333335,
        "state": {
          "batch_size": 1,
          "prompt_characters": 14,
          "regex_cache_entries": 15,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 220229.0,
        "unexplained_share": 0.0670267264058643
      },
      {
        "calls": 3,
        "instructions_per_call": 3377144.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "regex_cache_entries": 15,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 306946.3333333333,
        "unexplained_share": 0.09088932344410938
      },
      {
        "calls": 3,
        "instructions_per_call": 3385972.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 13,
          "regex_cache_entries": 15,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 307760.00000000006,
        "unexplained_share": 0.09089265947857811
      },
      {
        "calls": 3,
        "instructions_per_call": 3357670.6666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "regex_cache_entries": 15,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 276568.99999999994,
        "unexplained_share": 0.08236930522866447
      },
      {
        "calls": 3,
        "instructions_per_call": 3376313.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 21,
          "regex_cache_entries": 15,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 281904.3333333332,
        "unexplained_share": 0.08349472733521246
      },
      {
        "calls": 3,
        "instructions_per_call": 3597458.6666666665,
        "state": {
          "batch_size": 2,
          "prompt_characters": 8,
          "regex_cache_entries": 15,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 334619.6666666666,
        "unexplained_share": 0.09301556950943887
      },
      {
        "calls": 3,
        "instructions_per_call": 3561340.0,
        "state": {
          "batch_size": 2,
          "prompt_characters": 17,
          "regex_cache_entries": 15,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 291172.66666666657,
        "unexplained_share": 0.08175930033826216
      },
      {
        "calls": 3,
        "instructions_per_call": 3639562.0,
        "state": {
          "batch_size": 2,
          "prompt_characters": 8,
          "regex_cache_entries": 15,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 340827.3333333333,
        "unexplained_share": 0.09364515107403949
      },
      {
        "calls": 3,
        "instructions_per_call": 3652703.6666666665,
        "state": {
          "batch_size": 2,
          "prompt_characters": 24,
          "regex_cache_entries": 15,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 343330.0,
        "unexplained_share": 0.0939933899191202
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 12.147983827317264,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 12.147983827317264,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14"
  }
}