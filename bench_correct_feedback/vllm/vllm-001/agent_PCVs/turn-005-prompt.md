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
    "hypothesis": "Rescaling did not help. A quadratic length term and an interaction between special-token processing and truncation should better explain the ordinary-call costs while preserving the exceptional default-options state.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "int(tokenization_kwargs is None)",
        "name": "default_options",
        "rationale": "Separates the entry state containing the exceptional initialization cost."
      },
      {
        "expression": "len(prompt if isinstance(prompt, str) else prompt['prompt'])",
        "name": "prompt_chars",
        "rationale": "Models tokenizer work that grows linearly with input length."
      },
      {
        "expression": "len(prompt if isinstance(prompt, str) else prompt['prompt']) ** 2",
        "name": "prompt_chars_squared",
        "rationale": "Allows curvature in text-processing cost that the previous linear model could not explain."
      },
      {
        "expression": "int((tokenization_kwargs or {}).get('add_special_tokens', True) and 'truncate_prompt_tokens' not in (tokenization_kwargs or {}))",
        "name": "special_tokens_without_truncation",
        "rationale": "Captures the observed special-token cost increase before explicit truncation options are supplied."
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
        "default_options": 10446416.316898234,
        "prompt_chars": 1364.0476500042007,
        "prompt_chars_squared": 2.42379665691942,
        "special_tokens_without_truncation": 7092.219004428952
      },
      "constant": 308194.05295154126,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 107.97435522032902,
    "max_unexplained_share": 0.21344115481990392,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_options",
      "prompt_chars",
      "prompt_chars_squared",
      "special_tokens_without_truncation"
    ],
    "raw_files": [
      "run.1776522.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 415544.0,
        "state": {
          "default_options": 0,
          "prompt_chars": 21,
          "prompt_chars_squared": 441,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 85549.0,
        "unexplained_share": 0.20587230233140172
      },
      {
        "calls": 1,
        "instructions_per_call": 417428.0,
        "state": {
          "default_options": 0,
          "prompt_chars": 33,
          "prompt_chars_squared": 1089,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 68245.0,
        "unexplained_share": 0.16348927240146804
      },
      {
        "calls": 4,
        "instructions_per_call": 514927.75,
        "state": {
          "default_options": 0,
          "prompt_chars": 83,
          "prompt_chars_squared": 6889,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 85170.75,
        "unexplained_share": 0.16540330172533912
      },
      {
        "calls": 3,
        "instructions_per_call": 566634.3333333334,
        "state": {
          "default_options": 0,
          "prompt_chars": 83,
          "prompt_chars_squared": 6889,
          "special_tokens_without_truncation": 1
        },
        "unexplained_instructions_per_call": 110069.33333333331,
        "unexplained_share": 0.19425108373830738
      },
      {
        "calls": 17,
        "instructions_per_call": 722650.7647058824,
        "state": {
          "default_options": 0,
          "prompt_chars": 156,
          "prompt_chars_squared": 24336,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 147454.82352941183,
        "unexplained_share": 0.20404714245258662
      },
      {
        "calls": 5,
        "instructions_per_call": 763187.4,
        "state": {
          "default_options": 0,
          "prompt_chars": 156,
          "prompt_chars_squared": 24336,
          "special_tokens_without_truncation": 1
        },
        "unexplained_instructions_per_call": 162895.59999999995,
        "unexplained_share": 0.21344115481990392
      },
      {
        "calls": 4,
        "instructions_per_call": 731882.75,
        "state": {
          "default_options": 0,
          "prompt_chars": 162,
          "prompt_chars_squared": 26244,
          "special_tokens_without_truncation": 0
        },
        "unexplained_instructions_per_call": 148532.5,
        "unexplained_share": 0.20294575872979653
      },
      {
        "calls": 1,
        "instructions_per_call": 11036311.0,
        "state": {
          "default_options": 1,
          "prompt_chars": 21,
          "prompt_chars_squared": 441,
          "special_tokens_without_truncation": 1
        },
        "unexplained_instructions_per_call": 232356.0,
        "unexplained_share": 0.021053774218577202
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 21.344115481990393,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 21.344115481990393,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29"
  }
}