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
    "hypothesis": "A piecewise prompt-length model may explain the observed cost regimes better than sampling settings. The short-prompt indicators may proxy startup effects in this fixed workload; they do not establish prompt length as their cause.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0",
        "name": "prompt_tokens",
        "rationale": "Retains the prompt-copying size term."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 9)",
        "name": "nine_token_prompt",
        "rationale": "Separates the observed nine-token state, whose cost substantially exceeds the general baseline."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 10)",
        "name": "ten_token_prompt",
        "rationale": "Separates the highest-cost observed prompt-length state."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and 12 <= len(request.prompt_token_ids) < 23)",
        "name": "medium_prompt",
        "rationale": "Tests the elevated instruction-cost regime observed for medium prompts."
      }
    ]
  },
  "case_id": "vllm-042",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-042",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "medium_prompt": 3189.4795793758485,
        "nine_token_prompt": 15749.849156490282,
        "prompt_tokens": 6.344640434192674,
        "ten_token_prompt": 31663.702905924918
      },
      "constant": 44495.2649559023,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 123.79665974201635,
    "max_unexplained_share": 0.10202131569276002,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "nine_token_prompt",
      "ten_token_prompt",
      "medium_prompt"
    ],
    "raw_files": [
      "run.2291347.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 68025.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 1,
          "prompt_tokens": 9,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 6940.0,
        "unexplained_share": 0.10202131569276002
      },
      {
        "calls": 1,
        "instructions_per_call": 84907.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 10,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 8128.0,
        "unexplained_share": 0.09572826739844771
      },
      {
        "calls": 1,
        "instructions_per_call": 46793.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 11,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3002.0,
        "unexplained_share": 0.0641548949629218
      },
      {
        "calls": 4,
        "instructions_per_call": 51543.5,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "prompt_tokens": 21,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4035.0,
        "unexplained_share": 0.07828339169827428
      },
      {
        "calls": 3,
        "instructions_per_call": 54604.666666666664,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "prompt_tokens": 22,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4834.0,
        "unexplained_share": 0.08852723210470412
      },
      {
        "calls": 10,
        "instructions_per_call": 46867.6,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 45,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 2960.0,
        "unexplained_share": 0.06315663699442686
      },
      {
        "calls": 12,
        "instructions_per_call": 47713.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 46,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3234.1666666666665,
        "unexplained_share": 0.06778376263631854
      },
      {
        "calls": 4,
        "instructions_per_call": 46801.25,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 47,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3028.5,
        "unexplained_share": 0.06470981010122592
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 10.202131569276002,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 10.202131569276002,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}