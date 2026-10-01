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
    "hypothesis": "Separating the exceptional default-options state should prevent its cost from distorting the fit. Remaining costs should largely follow text length and special-token processing, with smaller option-handling costs.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(prompt if isinstance(prompt, str) else prompt['prompt'])",
        "name": "prompt_chars",
        "rationale": "Captures text-length-dependent tokenization work."
      },
      {
        "expression": "int(tokenization_kwargs is None)",
        "name": "default_tokenization_options",
        "rationale": "Separates the default-options entry state, which contains the observed exceptionally expensive call."
      },
      {
        "expression": "int((tokenization_kwargs or {}).get('add_special_tokens', True))",
        "name": "add_special_tokens",
        "rationale": "Special-token processing plausibly explains the higher costs in alternating batches with similar text lengths."
      },
      {
        "expression": "len(tokenization_kwargs or {})",
        "name": "tokenization_option_count",
        "rationale": "Captures option merging and validation while preserving distinctions among entry states."
      }
    ]
  },
  "case_id": "vllm-001",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-001",
    "distinct_states": 10,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "add_special_tokens": 1795.7484353575667,
        "default_tokenization_options": 10438527.724043848,
        "prompt_chars": 1772.4199296412473,
        "tokenization_option_count": -2597.3104822261844
      },
      "constant": 290755.2210880901,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 108.10026272805408,
    "max_unexplained_share": 0.2506422264584457,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_chars",
      "default_tokenization_options",
      "add_special_tokens",
      "tokenization_option_count"
    ],
    "raw_files": [
      "run.1774529.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 410751.0,
        "state": {
          "add_special_tokens": 0,
          "default_tokenization_options": 0,
          "prompt_chars": 21,
          "tokenization_option_count": 1
        },
        "unexplained_instructions_per_call": 89916.0,
        "unexplained_share": 0.21890634471979376
      },
      {
        "calls": 1,
        "instructions_per_call": 11054982.0,
        "state": {
          "add_special_tokens": 1,
          "default_tokenization_options": 1,
          "prompt_chars": 21,
          "tokenization_option_count": 0
        },
        "unexplained_instructions_per_call": 275029.0,
        "unexplained_share": 0.02487828564533167
      },
      {
        "calls": 1,
        "instructions_per_call": 416203.0,
        "state": {
          "add_special_tokens": 0,
          "default_tokenization_options": 0,
          "prompt_chars": 33,
          "tokenization_option_count": 1
        },
        "unexplained_instructions_per_call": 74607.0,
        "unexplained_share": 0.1792562763843605
      },
      {
        "calls": 4,
        "instructions_per_call": 515924.5,
        "state": {
          "add_special_tokens": 0,
          "default_tokenization_options": 0,
          "prompt_chars": 83,
          "tokenization_option_count": 3
        },
        "unexplained_instructions_per_call": 97121.75,
        "unexplained_share": 0.1882479897736975
      },
      {
        "calls": 3,
        "instructions_per_call": 566413.0,
        "state": {
          "add_special_tokens": 1,
          "default_tokenization_options": 0,
          "prompt_chars": 83,
          "tokenization_option_count": 2
        },
        "unexplained_instructions_per_call": 122438.66666666664,
        "unexplained_share": 0.21616500092100047
      },
      {
        "calls": 6,
        "instructions_per_call": 722588.8333333334,
        "state": {
          "add_special_tokens": 0,
          "default_tokenization_options": 0,
          "prompt_chars": 156,
          "tokenization_option_count": 5
        },
        "unexplained_instructions_per_call": 175599.33333333337,
        "unexplained_share": 0.24301418072472292
      },
      {
        "calls": 4,
        "instructions_per_call": 719457.25,
        "state": {
          "add_special_tokens": 0,
          "default_tokenization_options": 0,
          "prompt_chars": 156,
          "tokenization_option_count": 7
        },
        "unexplained_instructions_per_call": 172936.75,
        "unexplained_share": 0.24037112698495985
      },
      {
        "calls": 5,
        "instructions_per_call": 763048.6,
        "state": {
          "add_special_tokens": 1,
          "default_tokenization_options": 0,
          "prompt_chars": 156,
          "tokenization_option_count": 4
        },
        "unexplained_instructions_per_call": 191252.19999999995,
        "unexplained_share": 0.2506422264584457
      },
      {
        "calls": 7,
        "instructions_per_call": 729610.0,
        "state": {
          "add_special_tokens": 1,
          "default_tokenization_options": 0,
          "prompt_chars": 156,
          "tokenization_option_count": 6
        },
        "unexplained_instructions_per_call": 176987.7142857143,
        "unexplained_share": 0.24257852042284822
      },
      {
        "calls": 4,
        "instructions_per_call": 734200.25,
        "state": {
          "add_special_tokens": 0,
          "default_tokenization_options": 0,
          "prompt_chars": 162,
          "tokenization_option_count": 7
        },
        "unexplained_instructions_per_call": 177255.0,
        "unexplained_share": 0.24142595974327166
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 25.06422264584457,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 25.06422264584457,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29"
  }
}