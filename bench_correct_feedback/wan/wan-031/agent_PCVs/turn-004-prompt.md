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
    "hypothesis": "Loaded-module cardinality was constant and could not explain the variation. Existing source-cache cardinality tests a different runtime initialization state that can change without additional imports.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "len(__import__('sys').modules['linecache'].cache) if 'linecache' in __import__('sys').modules else 0",
        "name": "source_cache_entries",
        "rationale": "Tests whether populated runtime source caches distinguish warmup states; reads an existing cache without loading source files."
      },
      {
        "expression": "1 if isinstance(prompt, str) else len(prompt)",
        "name": "batch_size",
        "rationale": "Models per-prompt cleaning, tokenization, and embedding reconstruction."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length",
        "name": "token_positions",
        "rationale": "Models encoder and tensor processing over padded sequences."
      },
      {
        "expression": "len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))",
        "name": "prompt_characters",
        "rationale": "Models text processing and preserves distinctions between positive and negative prompts."
      }
    ]
  },
  "case_id": "wan-031",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-031",
    "distinct_states": 11,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "batch_size": 120178.22019741833,
        "prompt_characters": 116.80853178711948,
        "source_cache_entries": 0.0,
        "token_positions": 2632.728696417476
      },
      "constant": 2276401.1406055503,
      "dependent_columns": [
        0
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 30.115099227055907,
    "max_unexplained_share": 0.34221492122023883,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "source_cache_entries",
      "batch_size",
      "token_positions",
      "prompt_characters"
    ],
    "raw_files": [
      "run.1581275.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3274888.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "source_cache_entries": 45,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 876161.1666666665,
        "unexplained_share": 0.267539276661268
      },
      {
        "calls": 3,
        "instructions_per_call": 3757373.6666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 8,
          "source_cache_entries": 45,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 1285829.3333333333,
        "unexplained_share": 0.34221492122023883
      },
      {
        "calls": 3,
        "instructions_per_call": 3285321.6666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 14,
          "source_cache_entries": 45,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 879913.6666666665,
        "unexplained_share": 0.26783181555535146
      },
      {
        "calls": 3,
        "instructions_per_call": 3372974.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "source_cache_entries": 45,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 959553.6666666664,
        "unexplained_share": 0.284482971605078
      },
      {
        "calls": 3,
        "instructions_per_call": 3378763.3333333335,
        "state": {
          "batch_size": 1,
          "prompt_characters": 13,
          "source_cache_entries": 45,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 958833.6666666667,
        "unexplained_share": 0.2837824292714593
      },
      {
        "calls": 3,
        "instructions_per_call": 3360521.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "source_cache_entries": 45,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 935051.0000000001,
        "unexplained_share": 0.27824584342725434
      },
      {
        "calls": 3,
        "instructions_per_call": 3376703.3333333335,
        "state": {
          "batch_size": 1,
          "prompt_characters": 21,
          "source_cache_entries": 45,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 939773.6666666664,
        "unexplained_share": 0.2783109956357827
      },
      {
        "calls": 3,
        "instructions_per_call": 3595099.3333333335,
        "state": {
          "batch_size": 2,
          "prompt_characters": 8,
          "source_cache_entries": 45,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 1029837.3333333336,
        "unexplained_share": 0.28645587725067967
      },
      {
        "calls": 3,
        "instructions_per_call": 3561735.3333333335,
        "state": {
          "batch_size": 2,
          "prompt_characters": 17,
          "source_cache_entries": 45,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 990791.6666666669,
        "unexplained_share": 0.2781766678152953
      },
      {
        "calls": 3,
        "instructions_per_call": 3642696.0,
        "state": {
          "batch_size": 2,
          "prompt_characters": 8,
          "source_cache_entries": 45,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 1040701.6666666669,
        "unexplained_share": 0.2856954482796991
      },
      {
        "calls": 3,
        "instructions_per_call": 3654594.3333333335,
        "state": {
          "batch_size": 2,
          "prompt_characters": 24,
          "source_cache_entries": 45,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 1043176.0000000002,
        "unexplained_share": 0.28544235142194996
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 34.22149212202388,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 34.22149212202388,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14"
  }
}