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
    "hypothesis": "The remaining unexplained work may scale with lexical units rather than a polynomial of character length. Combining word count and character count should better represent tokenizer and token-list processing costs.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "int(tokenization_kwargs is None)",
        "name": "default_options",
        "rationale": "Separates the entry state containing the exceptional initialization cost."
      },
      {
        "expression": "len(prompt if isinstance(prompt, str) else prompt['prompt'])",
        "name": "prompt_chars",
        "rationale": "Captures character scanning and text conversion work."
      },
      {
        "expression": "(prompt if isinstance(prompt, str) else prompt['prompt']).count(' ') + 1",
        "name": "prompt_word_count",
        "rationale": "Provides a cheap lexical-unit count to distinguish token-dependent work from character-dependent work."
      },
      {
        "expression": "int((tokenization_kwargs or {}).get('add_special_tokens', True) and 'truncate_prompt_tokens' not in (tokenization_kwargs or {}))",
        "name": "special_tokens_without_truncation",
        "rationale": "Captures the higher observed cost of special-token processing without explicit truncation."
      }
    ]
  },
  "case_id": "vllm-001",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-001",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "default_options": 10560893.967123834,
        "prompt_chars": 7527.822870935013,
        "prompt_word_count": -32167.956893402396,
        "special_tokens_without_truncation": 8004.124116697394
      },
      "constant": 351086.81215122115,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 122.51427848404273,
    "max_unexplained_share": 0.1743826563195479,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_options",
      "prompt_chars",
      "prompt_word_count",
      "special_tokens_without_truncation"
    ],
    "raw_files": [
      "run.1777426.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 413384.0,
        "state": {
          "default_options": 0,
          "prompt_chars": 21,
          "prompt_word_count": 5,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 72087.0,
        "unexplained_share": 0.1743826563195479
      },
      {
        "calls": 1,
        "instructions_per_call": 419645.0,
        "state": {
          "default_options": 0,
          "prompt_chars": 33,
          "prompt_word_count": 7,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 53054.0,
        "unexplained_share": 0.12642590761238667
      },
      {
        "calls": 4,
        "instructions_per_call": 514404.75,
        "state": {
          "default_options": 0,
          "prompt_chars": 83,
          "prompt_word_count": 16,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 60859.75,
        "unexplained_share": 0.11831101870657298
      },
      {
        "calls": 3,
        "instructions_per_call": 565146.6666666666,
        "state": {
          "default_options": 0,
          "prompt_chars": 83,
          "prompt_word_count": 16,
          "special_tokens_without_truncation": 1
        },
        "unexplained_instructions_per_call": 83661.33333333331,
        "unexplained_share": 0.14803472844807244
      },
      {
        "calls": 17,
        "instructions_per_call": 723170.8823529412,
        "state": {
          "default_options": 0,
          "prompt_chars": 156,
          "prompt_word_count": 28,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 104237.99999999999,
        "unexplained_share": 0.1441402060614589
      },
      {
        "calls": 5,
        "instructions_per_call": 762118.2,
        "state": {
          "default_options": 0,
          "prompt_chars": 156,
          "prompt_word_count": 28,
          "special_tokens_without_truncation": 1
        },
        "unexplained_instructions_per_call": 117480.19999999997,
        "unexplained_share": 0.1541495794221946
      },
      {
        "calls": 4,
        "instructions_per_call": 734629.5,
        "state": {
          "default_options": 0,
          "prompt_chars": 162,
          "prompt_word_count": 29,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 104637.75,
        "unexplained_share": 0.14243608512862607
      },
      {
        "calls": 1,
        "instructions_per_call": 11055277.0,
        "state": {
          "default_options": 1,
          "prompt_chars": 21,
          "prompt_word_count": 5,
          "special_tokens_without_truncation": 1
        },
        "unexplained_instructions_per_call": 126270.0,
        "unexplained_share": 0.01142169481596888
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.438265631954792,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.438265631954792,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29"
  }
}