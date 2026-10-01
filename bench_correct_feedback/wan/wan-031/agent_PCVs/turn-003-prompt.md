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
    "hypothesis": "Runtime initialization contributes more variation than quadratic attention at these small sequence lengths. Loaded-module cardinality may distinguish initialization regimes that input dimensions alone cannot explain.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(__import__('sys').modules)",
        "name": "loaded_modules",
        "rationale": "Measures existing runtime initialization state cheaply; repeated calls with identical dimensions showed substantial unexplained variation consistent with warmup."
      },
      {
        "expression": "1 if isinstance(prompt, str) else len(prompt)",
        "name": "batch_size",
        "rationale": "Captures per-prompt tokenizer and embedding reconstruction overhead."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length",
        "name": "token_positions",
        "rationale": "Captures padded encoder processing and tensor operations."
      },
      {
        "expression": "len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))",
        "name": "prompt_characters",
        "rationale": "Captures cleaning and tokenization work while retaining distinct prompt states."
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
        "batch_size": 120171.07513632908,
        "loaded_modules": 0.0,
        "prompt_characters": 110.7189093670187,
        "token_positions": 2651.786963484501
      },
      "constant": 2274051.4700341853,
      "dependent_columns": [
        0
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 29.892772560939193,
    "max_unexplained_share": 0.34189121346047896,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "loaded_modules",
      "batch_size",
      "token_positions",
      "prompt_characters"
    ],
    "raw_files": [
      "run.1580759.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3270688.8333333335,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 4,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 874056.8333333331,
        "unexplained_share": 0.26723937307192114
      },
      {
        "calls": 3,
        "instructions_per_call": 3752694.6666666665,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 8,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 1283013.3333333342,
        "unexplained_share": 0.34189121346047896
      },
      {
        "calls": 3,
        "instructions_per_call": 3278760.6666666665,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 14,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 875768.6666666664,
        "unexplained_share": 0.2671035661645324
      },
      {
        "calls": 3,
        "instructions_per_call": 3372047.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 4,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 959070.0000000001,
        "unexplained_share": 0.2844177438807941
      },
      {
        "calls": 3,
        "instructions_per_call": 3379326.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 13,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 959806.3333333335,
        "unexplained_share": 0.2840230073491973
      },
      {
        "calls": 3,
        "instructions_per_call": 3350809.3333333335,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 4,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 928594.0000000002,
        "unexplained_share": 0.2771252875424724
      },
      {
        "calls": 3,
        "instructions_per_call": 3367731.0,
        "state": {
          "batch_size": 1,
          "loaded_modules": 3597,
          "prompt_characters": 21,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 934219.6666666667,
        "unexplained_share": 0.2774032922067311
      },
      {
        "calls": 3,
        "instructions_per_call": 3586732.6666666665,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "prompt_characters": 8,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 1024356.6666666671,
        "unexplained_share": 0.2855960457233223
      },
      {
        "calls": 3,
        "instructions_per_call": 3554483.6666666665,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "prompt_characters": 17,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 986358.3333333334,
        "unexplained_share": 0.2774969379049991
      },
      {
        "calls": 3,
        "instructions_per_call": 3637718.6666666665,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "prompt_characters": 8,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 1037536.3333333334,
        "unexplained_share": 0.28521621059939034
      },
      {
        "calls": 3,
        "instructions_per_call": 3651701.0,
        "state": {
          "batch_size": 2,
          "loaded_modules": 3597,
          "prompt_characters": 24,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 1042226.6666666669,
        "unexplained_share": 0.2854085443103548
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 34.1891213460479,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 34.1891213460479,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14"
  }
}