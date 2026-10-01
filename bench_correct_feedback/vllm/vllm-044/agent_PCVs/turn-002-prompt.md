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
    "hypothesis": "Instruction count is dominated by fixed request processing plus linear token validation, with additional variation from raw-prompt preprocessing and sampling-specific branches.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(prompt.get('prompt_token_ids', ())) if isinstance(prompt, dict) else 0",
        "name": "prompt_token_count",
        "rationale": "Token validation scans prompt IDs for minimum and maximum values, producing cost proportional to token count."
      },
      {
        "expression": "len(prompt) if isinstance(prompt, str) else len(prompt.get('prompt', '')) if isinstance(prompt, dict) and 'type' not in prompt else 0",
        "name": "raw_prompt_characters",
        "rationale": "If raw prompts reach this boundary, their character count approximates tokenization and preprocessing work."
      },
      {
        "expression": "int(isinstance(params, SamplingParams) and params.temperature > 0)",
        "name": "sampling_enabled",
        "rationale": "Separates sampling parameter validation and processing paths from greedy generation."
      }
    ]
  },
  "case_id": "vllm-044",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-044",
    "distinct_states": 13,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "prompt_token_count": 110.96017506067132,
        "raw_prompt_characters": 0.0,
        "sampling_enabled": -376.0
      },
      "constant": 34872.20408022178,
      "dependent_columns": [
        1
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 125.4382627857849,
    "max_unexplained_share": 0.9984690982475398,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_token_count",
      "raw_prompt_characters",
      "sampling_enabled"
    ],
    "raw_files": [
      "run.2298978.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 432702.0,
        "state": {
          "prompt_token_count": 9,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 395594.0,
        "unexplained_share": 0.9142412098857875
      },
      {
        "calls": 1,
        "instructions_per_call": 48453142.0,
        "state": {
          "prompt_token_count": 10,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 48378965.0,
        "unexplained_share": 0.9984690982475398
      },
      {
        "calls": 1,
        "instructions_per_call": 399492.0,
        "state": {
          "prompt_token_count": 11,
          "raw_prompt_characters": 0,
          "sampling_enabled": 1
        },
        "unexplained_instructions_per_call": 367514.0,
        "unexplained_share": 0.9199533407427433
      },
      {
        "calls": 3,
        "instructions_per_call": 410885.3333333333,
        "state": {
          "prompt_token_count": 21,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 377360.6666666667,
        "unexplained_share": 0.9184087044560689
      },
      {
        "calls": 1,
        "instructions_per_call": 407867.0,
        "state": {
          "prompt_token_count": 21,
          "raw_prompt_characters": 0,
          "sampling_enabled": 1
        },
        "unexplained_instructions_per_call": 374783.0,
        "unexplained_share": 0.9188853229116354
      },
      {
        "calls": 2,
        "instructions_per_call": 413292.5,
        "state": {
          "prompt_token_count": 22,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 379314.5,
        "unexplained_share": 0.917787039445429
      },
      {
        "calls": 1,
        "instructions_per_call": 420831.0,
        "state": {
          "prompt_token_count": 22,
          "raw_prompt_characters": 0,
          "sampling_enabled": 1
        },
        "unexplained_instructions_per_call": 387296.0,
        "unexplained_share": 0.9203124294550544
      },
      {
        "calls": 7,
        "instructions_per_call": 413502.71428571426,
        "state": {
          "prompt_token_count": 45,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 377277.7142857142,
        "unexplained_share": 0.9123947709446715
      },
      {
        "calls": 3,
        "instructions_per_call": 415316.0,
        "state": {
          "prompt_token_count": 45,
          "raw_prompt_characters": 0,
          "sampling_enabled": 1
        },
        "unexplained_instructions_per_call": 379462.9999999999,
        "unexplained_share": 0.9136729622745088
      },
      {
        "calls": 8,
        "instructions_per_call": 414623.75,
        "state": {
          "prompt_token_count": 46,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 378254.375,
        "unexplained_share": 0.9122834256358928
      },
      {
        "calls": 4,
        "instructions_per_call": 415327.25,
        "state": {
          "prompt_token_count": 46,
          "raw_prompt_characters": 0,
          "sampling_enabled": 1
        },
        "unexplained_instructions_per_call": 379061.75,
        "unexplained_share": 0.9126821079040685
      },
      {
        "calls": 2,
        "instructions_per_call": 413287.0,
        "state": {
          "prompt_token_count": 47,
          "raw_prompt_characters": 0,
          "sampling_enabled": 0
        },
        "unexplained_instructions_per_call": 376799.5,
        "unexplained_share": 0.9117138937348622
      },
      {
        "calls": 2,
        "instructions_per_call": 409773.5,
        "state": {
          "prompt_token_count": 47,
          "raw_prompt_characters": 0,
          "sampling_enabled": 1
        },
        "unexplained_instructions_per_call": 373779.5,
        "unexplained_share": 0.9121612305334532
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "26e864dcd3e0d2ad1b3e80a4999c787ab33577dbf46d93f5153ab2856c763213",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 99.84690982475398,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 99.84690982475398,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "26e864dcd3e0d2ad1b3e80a4999c787ab33577dbf46d93f5153ab2856c763213"
  }
}