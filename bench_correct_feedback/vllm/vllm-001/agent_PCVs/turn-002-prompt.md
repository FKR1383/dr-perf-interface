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
    "hypothesis": "Instruction count is primarily a fixed preprocessing cost plus text-length-dependent tokenization, with additional costs for structured prompts, option handling, and explicit truncation.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(prompt if isinstance(prompt, str) else prompt['prompt'])",
        "name": "prompt_chars",
        "rationale": "Text length predicts tokenizer scanning and token construction work."
      },
      {
        "expression": "int(isinstance(prompt, dict))",
        "name": "structured_prompt",
        "rationale": "Dictionary prompts take a distinct prompt parsing path."
      },
      {
        "expression": "len(tokenization_kwargs or {})",
        "name": "tokenization_option_count",
        "rationale": "Option merging and validation depend on the number of supplied tokenization options."
      },
      {
        "expression": "int('truncate_prompt_tokens' in (tokenization_kwargs or {}))",
        "name": "explicit_truncation",
        "rationale": "Explicit truncation can introduce additional tokenization configuration and token processing work."
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
        "explicit_truncation": -2557.2281568966773,
        "prompt_chars": 1212.274699099589,
        "structured_prompt": 135.08725641306157,
        "tokenization_option_count": -7578.765166428881
      },
      "constant": 231283.07705118592,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 106.10250392090529,
    "max_unexplained_share": 0.9724041142621516,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_chars",
      "structured_prompt",
      "tokenization_option_count",
      "explicit_truncation"
    ],
    "raw_files": [
      "run.1773455.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 11058605.0,
        "state": {
          "explicit_truncation": 0,
          "prompt_chars": 21,
          "structured_prompt": 0,
          "tokenization_option_count": 0
        },
        "unexplained_instructions_per_call": 10753433.0,
        "unexplained_share": 0.9724041142621516
      },
      {
        "calls": 1,
        "instructions_per_call": 413207.0,
        "state": {
          "explicit_truncation": 0,
          "prompt_chars": 21,
          "structured_prompt": 0,
          "tokenization_option_count": 1
        },
        "unexplained_instructions_per_call": 186074.0,
        "unexplained_share": 0.4503166693691056
      },
      {
        "calls": 1,
        "instructions_per_call": 419857.0,
        "state": {
          "explicit_truncation": 0,
          "prompt_chars": 33,
          "structured_prompt": 0,
          "tokenization_option_count": 1
        },
        "unexplained_instructions_per_call": 178858.0,
        "unexplained_share": 0.42599742293209353
      },
      {
        "calls": 3,
        "instructions_per_call": 566439.3333333334,
        "state": {
          "explicit_truncation": 0,
          "prompt_chars": 83,
          "structured_prompt": 0,
          "tokenization_option_count": 2
        },
        "unexplained_instructions_per_call": 260992.33333333326,
        "unexplained_share": 0.46075955177312294
      },
      {
        "calls": 4,
        "instructions_per_call": 516058.25,
        "state": {
          "explicit_truncation": 0,
          "prompt_chars": 83,
          "structured_prompt": 1,
          "tokenization_option_count": 3
        },
        "unexplained_instructions_per_call": 223026.0,
        "unexplained_share": 0.4321721433578477
      },
      {
        "calls": 5,
        "instructions_per_call": 760712.0,
        "state": {
          "explicit_truncation": 0,
          "prompt_chars": 156,
          "structured_prompt": 0,
          "tokenization_option_count": 4
        },
        "unexplained_instructions_per_call": 368295.6000000001,
        "unexplained_share": 0.4841459054149272
      },
      {
        "calls": 6,
        "instructions_per_call": 719921.5,
        "state": {
          "explicit_truncation": 1,
          "prompt_chars": 156,
          "structured_prompt": 0,
          "tokenization_option_count": 5
        },
        "unexplained_instructions_per_call": 344692.3333333332,
        "unexplained_share": 0.478791553430941
      },
      {
        "calls": 4,
        "instructions_per_call": 715980.5,
        "state": {
          "explicit_truncation": 1,
          "prompt_chars": 156,
          "structured_prompt": 0,
          "tokenization_option_count": 7
        },
        "unexplained_instructions_per_call": 340636.0,
        "unexplained_share": 0.47576156054529417
      },
      {
        "calls": 7,
        "instructions_per_call": 726519.1428571428,
        "state": {
          "explicit_truncation": 1,
          "prompt_chars": 156,
          "structured_prompt": 1,
          "tokenization_option_count": 6
        },
        "unexplained_instructions_per_call": 348899.8571428572,
        "unexplained_share": 0.4802349126972174
      },
      {
        "calls": 4,
        "instructions_per_call": 729768.5,
        "state": {
          "explicit_truncation": 1,
          "prompt_chars": 162,
          "structured_prompt": 0,
          "tokenization_option_count": 7
        },
        "unexplained_instructions_per_call": 347118.5,
        "unexplained_share": 0.4756556359996355
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 97.24041142621516,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 97.24041142621516,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29"
  }
}