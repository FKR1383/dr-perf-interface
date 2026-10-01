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
    "hypothesis": "The flat medium-prompt indicator performed better than its ramp replacement. Combining it with a decreasing prompt-length basis may capture cost components that the previous positive length term could not explain, while retaining the startup proxies.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "max(0, self.vllm_config.model_config.max_model_len - len(request.prompt_token_ids)) if request.prompt_token_ids is not None else 0",
        "name": "prompt_headroom",
        "rationale": "Tests a decreasing length basis, allowing fitted cost components to be larger for shorter prompts."
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
        "expression": "int(request.prompt_token_ids is not None and 12 <= len(request.prompt_token_ids) < 23)",
        "name": "medium_prompt",
        "rationale": "Restores the flat medium-prompt indicator from the best-performing candidate."
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
        "medium_prompt": 2777.7167571234736,
        "nine_token_prompt": 14856.6102125735,
        "prompt_headroom": -8.645952057892355,
        "ten_token_prompt": 31356.147976028962
      },
      "constant": 44265.492115841254,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 112.56353131867945,
    "max_unexplained_share": 0.11720526630760024,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_headroom",
      "nine_token_prompt",
      "ten_token_prompt",
      "medium_prompt"
    ],
    "raw_files": [
      "run.2292972.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 46185.5,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_headroom": 49,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3379.0,
        "unexplained_share": 0.0731614900780548
      },
      {
        "calls": 12,
        "instructions_per_call": 47602.583333333336,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_headroom": 50,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3791.6666666666665,
        "unexplained_share": 0.07965253986565854
      },
      {
        "calls": 10,
        "instructions_per_call": 46039.2,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_headroom": 51,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3219.2000000000003,
        "unexplained_share": 0.06992302212028012
      },
      {
        "calls": 3,
        "instructions_per_call": 53937.666666666664,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "prompt_headroom": 74,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 5297.0,
        "unexplained_share": 0.09820595378616057
      },
      {
        "calls": 4,
        "instructions_per_call": 50335.25,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "prompt_headroom": 75,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4230.0,
        "unexplained_share": 0.08403653503260637
      },
      {
        "calls": 1,
        "instructions_per_call": 46172.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_headroom": 85,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3424.0,
        "unexplained_share": 0.0741574980507667
      },
      {
        "calls": 1,
        "instructions_per_call": 84939.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "prompt_headroom": 86,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 9800.0,
        "unexplained_share": 0.11537691755259658
      },
      {
        "calls": 1,
        "instructions_per_call": 66840.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 1,
          "prompt_headroom": 87,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7834.0,
        "unexplained_share": 0.11720526630760024
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 11.720526630760023,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 11.720526630760023,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}