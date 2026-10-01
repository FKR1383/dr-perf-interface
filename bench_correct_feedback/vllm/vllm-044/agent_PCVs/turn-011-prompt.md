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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Scalar sampling settings did not explain the excess cost. This candidate tests the cloning branch and collection cardinalities that more directly determine parameter validation and copying work.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "len(prompt.get('prompt_token_ids', ())) if isinstance(prompt, dict) else 0",
        "name": "prompt_token_count",
        "rationale": "Captures the linear token-ID validation scans."
      },
      {
        "expression": "int(not getattr(params, 'skip_clone', False))",
        "name": "clone_required",
        "rationale": "Distinguishes parameter cloning from any configured clone bypass."
      },
      {
        "expression": "len(getattr(params, 'stop_token_ids', None) or ()) + len(getattr(params, '_all_stop_token_ids', None) or ())",
        "name": "stop_token_entries",
        "rationale": "Measures stop-token collection sizes relevant to cloning and generation-configuration updates."
      },
      {
        "expression": "len(getattr(params, 'allowed_token_ids', None) or ()) + len(getattr(params, 'bad_words', None) or ()) + len(getattr(params, 'logit_bias', None) or {})",
        "name": "tokenizer_constraint_entries",
        "rationale": "Measures optional tokenizer constraints that can add validation and copying work."
      }
    ]
  },
  "case_id": "vllm-044",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-044",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "clone_required": 0.0,
        "prompt_token_count": 102.0320347934141,
        "stop_token_entries": 0.0,
        "tokenizer_constraint_entries": 0.0
      },
      "constant": 37797.68841565702,
      "dependent_columns": [
        1,
        2,
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 105.14191988576204,
    "max_unexplained_share": 0.9984492170935032,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_token_count",
      "clone_required",
      "stop_token_entries",
      "tokenizer_constraint_entries"
    ],
    "raw_files": [
      "run.2304960.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 429915.0,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 9,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 392136.0,
        "unexplained_share": 0.912124489724713
      },
      {
        "calls": 1,
        "instructions_per_call": 48436180.0,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 10,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 48361066.0,
        "unexplained_share": 0.9984492170935032
      },
      {
        "calls": 1,
        "instructions_per_call": 400079.0,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 11,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 367644.0,
        "unexplained_share": 0.9189285116189553
      },
      {
        "calls": 4,
        "instructions_per_call": 408475.25,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 21,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 374608.0,
        "unexplained_share": 0.9170886118559203
      },
      {
        "calls": 3,
        "instructions_per_call": 415139.0,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 22,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 380712.66666666674,
        "unexplained_share": 0.9170727555509522
      },
      {
        "calls": 10,
        "instructions_per_call": 413505.2,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 45,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 376823.5999999997,
        "unexplained_share": 0.9112910792899331
      },
      {
        "calls": 12,
        "instructions_per_call": 414272.75,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 46,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 377428.6666666667,
        "unexplained_share": 0.9110632226393521
      },
      {
        "calls": 4,
        "instructions_per_call": 411246.75,
        "state": {
          "clone_required": 1,
          "prompt_token_count": 47,
          "stop_token_entries": 0,
          "tokenizer_constraint_entries": 0
        },
        "unexplained_instructions_per_call": 374483.75,
        "unexplained_share": 0.9106059804727941
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "26e864dcd3e0d2ad1b3e80a4999c787ab33577dbf46d93f5153ab2856c763213",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 99.84492170935032,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 99.84492170935032,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "26e864dcd3e0d2ad1b3e80a4999c787ab33577dbf46d93f5153ab2856c763213"
  }
}