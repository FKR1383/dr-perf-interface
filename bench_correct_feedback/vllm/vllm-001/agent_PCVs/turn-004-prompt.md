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
    "hypothesis": "The previous formula systematically underpredicts ordinary calls despite separating the exceptional call. Rescaling the same explanatory features tests whether numerical conditioning or coefficient regularization causes this bias.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "1000 * len(prompt if isinstance(prompt, str) else prompt['prompt'])",
        "name": "prompt_chars_scaled",
        "rationale": "Retains text-length dependence while increasing feature scale for numerical fitting."
      },
      {
        "expression": "1000 * int(tokenization_kwargs is None)",
        "name": "default_options_scaled",
        "rationale": "Separates the exceptionally expensive default-options state without requiring a multimillion-sized fitted coefficient."
      },
      {
        "expression": "1000 * int((tokenization_kwargs or {}).get('add_special_tokens', True))",
        "name": "special_tokens_scaled",
        "rationale": "Retains the special-token processing distinction at the same enlarged feature scale."
      },
      {
        "expression": "1000 * len(tokenization_kwargs or {})",
        "name": "option_count_scaled",
        "rationale": "Retains option-handling dependence and the observed state distinctions."
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
        "default_options_scaled": 10426.318339797604,
        "option_count_scaled": -2.4823800747716853,
        "prompt_chars_scaled": 1.7177119984626652,
        "special_tokens_scaled": 1.7329341847634374
      },
      "constant": 290250.1562305421,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 111.57792634982616,
    "max_unexplained_share": 0.261098656736017,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_chars_scaled",
      "default_options_scaled",
      "special_tokens_scaled",
      "option_count_scaled"
    ],
    "raw_files": [
      "run.1775561.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 416339.0,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 1000,
          "prompt_chars_scaled": 21000,
          "special_tokens_scaled": 0
        },
        "unexplained_instructions_per_call": 96629.0,
        "unexplained_share": 0.23209211724099832
      },
      {
        "calls": 1,
        "instructions_per_call": 11058042.0,
        "state": {
          "default_options_scaled": 1000,
          "option_count_scaled": 0,
          "prompt_chars_scaled": 21000,
          "special_tokens_scaled": 1000
        },
        "unexplained_instructions_per_call": 291374.0,
        "unexplained_share": 0.026349511061723223
      },
      {
        "calls": 1,
        "instructions_per_call": 418955.0,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 1000,
          "prompt_chars_scaled": 33000,
          "special_tokens_scaled": 0
        },
        "unexplained_instructions_per_call": 78868.0,
        "unexplained_share": 0.18824933465407978
      },
      {
        "calls": 4,
        "instructions_per_call": 517932.75,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 3000,
          "prompt_chars_scaled": 83000,
          "special_tokens_scaled": 0
        },
        "unexplained_instructions_per_call": 103817.0,
        "unexplained_share": 0.2004449419350292
      },
      {
        "calls": 3,
        "instructions_per_call": 567258.6666666666,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 2000,
          "prompt_chars_scaled": 83000,
          "special_tokens_scaled": 1000
        },
        "unexplained_instructions_per_call": 128887.99999999997,
        "unexplained_share": 0.22721204200787878
      },
      {
        "calls": 6,
        "instructions_per_call": 719932.6666666666,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 5000,
          "prompt_chars_scaled": 156000,
          "special_tokens_scaled": 0
        },
        "unexplained_instructions_per_call": 182429.33333333337,
        "unexplained_share": 0.2533977714582568
      },
      {
        "calls": 4,
        "instructions_per_call": 718982.25,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 7000,
          "prompt_chars_scaled": 156000,
          "special_tokens_scaled": 0
        },
        "unexplained_instructions_per_call": 180729.75,
        "unexplained_share": 0.2513688620268442
      },
      {
        "calls": 5,
        "instructions_per_call": 763051.8,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 4000,
          "prompt_chars_scaled": 156000,
          "special_tokens_scaled": 1000
        },
        "unexplained_instructions_per_call": 199231.7999999999,
        "unexplained_share": 0.261098656736017
      },
      {
        "calls": 7,
        "instructions_per_call": 728592.2857142857,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 6000,
          "prompt_chars_scaled": 156000,
          "special_tokens_scaled": 1000
        },
        "unexplained_instructions_per_call": 184474.85714285716,
        "unexplained_share": 0.25319353602818434
      },
      {
        "calls": 4,
        "instructions_per_call": 731878.75,
        "state": {
          "default_options_scaled": 0,
          "option_count_scaled": 7000,
          "prompt_chars_scaled": 162000,
          "special_tokens_scaled": 0
        },
        "unexplained_instructions_per_call": 184047.25,
        "unexplained_share": 0.2514723237968038
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 26.1098656736017,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 26.1098656736017,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "feed43640d9c3baa7e78ff9f5757681d2cde3dbb2df0ef27eb7e1143a6d55e29"
  }
}