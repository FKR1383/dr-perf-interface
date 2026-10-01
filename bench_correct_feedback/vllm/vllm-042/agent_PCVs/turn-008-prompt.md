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

This is iteration 8. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The strongest candidate used prompt length and three regime indicators. A length-weighted medium regime preserves that structure while allowing a small cost increase from 21 to 22 tokens.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0",
        "name": "prompt_tokens",
        "rationale": "Restores prompt length, which explained more variation than scheduler cardinality."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 9)",
        "name": "nine_token_prompt",
        "rationale": "Separates the elevated nine-token state."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 10)",
        "name": "ten_token_prompt",
        "rationale": "Separates the highest-cost observed state."
      },
      {
        "expression": "len(request.prompt_token_ids) if request.prompt_token_ids is not None and 12 <= len(request.prompt_token_ids) < 23 else 0",
        "name": "medium_prompt_tokens",
        "rationale": "Models medium-prompt overhead with modest length dependence, avoiding the previous ramp's doubling between 21 and 22 tokens."
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
        "medium_prompt_tokens": 156.6034462600508,
        "nine_token_prompt": 16466.664116064298,
        "prompt_tokens": 6.726039596911564,
        "ten_token_prompt": 33289.861206800415
      },
      "constant": 44155.947766625584,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 127.57407255563885,
    "max_unexplained_share": 0.10305780690435111,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "nine_token_prompt",
      "ten_token_prompt",
      "medium_prompt_tokens"
    ],
    "raw_files": [
      "run.2294797.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 68971.0,
        "state": {
          "medium_prompt_tokens": 0,
          "nine_token_prompt": 1,
          "prompt_tokens": 9,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7108.0,
        "unexplained_share": 0.10305780690435111
      },
      {
        "calls": 1,
        "instructions_per_call": 86304.0,
        "state": {
          "medium_prompt_tokens": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 10,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 8128.0,
        "unexplained_share": 0.09417871709306637
      },
      {
        "calls": 1,
        "instructions_per_call": 46751.0,
        "state": {
          "medium_prompt_tokens": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 11,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 2958.0,
        "unexplained_share": 0.06327137387435564
      },
      {
        "calls": 4,
        "instructions_per_call": 51199.75,
        "state": {
          "medium_prompt_tokens": 21,
          "nine_token_prompt": 0,
          "prompt_tokens": 21,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4001.5,
        "unexplained_share": 0.07815467848964107
      },
      {
        "calls": 3,
        "instructions_per_call": 54409.666666666664,
        "state": {
          "medium_prompt_tokens": 22,
          "nine_token_prompt": 0,
          "prompt_tokens": 22,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4758.666666666667,
        "unexplained_share": 0.08745994890613801
      },
      {
        "calls": 10,
        "instructions_per_call": 46072.9,
        "state": {
          "medium_prompt_tokens": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 45,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 2723.4,
        "unexplained_share": 0.05911067026386444
      },
      {
        "calls": 12,
        "instructions_per_call": 47028.5,
        "state": {
          "medium_prompt_tokens": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 46,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3024.0,
        "unexplained_share": 0.06430143423668626
      },
      {
        "calls": 4,
        "instructions_per_call": 45848.0,
        "state": {
          "medium_prompt_tokens": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 47,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 2726.0,
        "unexplained_share": 0.05945733728843134
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 10.30578069043511,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 10.30578069043511,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}