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
    "hypothesis": "Replacing the flat medium-prompt indicator with a ramp should better explain the difference between 21- and 22-token requests and reduce the remaining model error. Short-prompt indicators remain proxies for workload-specific startup effects.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0",
        "name": "prompt_tokens",
        "rationale": "Retains the prompt-size term and distinguishes eight observed lengths."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 9)",
        "name": "nine_token_prompt",
        "rationale": "Retains the indicator for the elevated nine-token state."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 10)",
        "name": "ten_token_prompt",
        "rationale": "Retains the indicator for the highest-cost observed state."
      },
      {
        "expression": "max(0, len(request.prompt_token_ids) - 20) if request.prompt_token_ids is not None and len(request.prompt_token_ids) < 23 else 0",
        "name": "medium_prompt_excess",
        "rationale": "Allows greater excess cost for 22-token prompts than for 21-token prompts, matching the observed medium-prompt variation."
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
        "medium_prompt_excess": 1154.53812725324,
        "nine_token_prompt": 17208.51837506902,
        "prompt_tokens": 8.674254603916982,
        "ten_token_prompt": 34047.54728149665
      },
      "constant": 42360.164863364356,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 127.48885772982612,
    "max_unexplained_share": 0.15089387016650826,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "nine_token_prompt",
      "ten_token_prompt",
      "medium_prompt_excess"
    ],
    "raw_files": [
      "run.2292168.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 68215.0,
        "state": {
          "medium_prompt_excess": 0,
          "nine_token_prompt": 1,
          "prompt_tokens": 9,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7802.0,
        "unexplained_share": 0.1143736714798798
      },
      {
        "calls": 1,
        "instructions_per_call": 85456.0,
        "state": {
          "medium_prompt_excess": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 10,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 8128.0,
        "unexplained_share": 0.09511327466766523
      },
      {
        "calls": 1,
        "instructions_per_call": 46832.0,
        "state": {
          "medium_prompt_excess": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 11,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 5194.0,
        "unexplained_share": 0.11090707208746156
      },
      {
        "calls": 4,
        "instructions_per_call": 51467.0,
        "state": {
          "medium_prompt_excess": 1,
          "nine_token_prompt": 0,
          "prompt_tokens": 21,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7489.5,
        "unexplained_share": 0.14552043056715955
      },
      {
        "calls": 3,
        "instructions_per_call": 54351.666666666664,
        "state": {
          "medium_prompt_excess": 2,
          "nine_token_prompt": 0,
          "prompt_tokens": 22,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 8201.333333333334,
        "unexplained_share": 0.15089387016650826
      },
      {
        "calls": 10,
        "instructions_per_call": 46422.5,
        "state": {
          "medium_prompt_excess": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 45,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4707.9,
        "unexplained_share": 0.10141418493187569
      },
      {
        "calls": 12,
        "instructions_per_call": 47903.5,
        "state": {
          "medium_prompt_excess": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 46,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 5355.416666666666,
        "unexplained_share": 0.11179593697050666
      },
      {
        "calls": 4,
        "instructions_per_call": 46677.25,
        "state": {
          "medium_prompt_excess": 0,
          "nine_token_prompt": 0,
          "prompt_tokens": 47,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 5015.5,
        "unexplained_share": 0.10745063173173226
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 15.089387016650827,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 15.089387016650827,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}