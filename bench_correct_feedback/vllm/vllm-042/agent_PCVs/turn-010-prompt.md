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

This is iteration 10. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "A shared short-prompt indicator plus an independent ten-token increment preserves separate fitting freedom without imposing the unsuccessful fixed ratio. This tests whether a hierarchical basis better explains shared startup-associated work.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0",
        "name": "prompt_tokens",
        "rationale": "Retains the prompt-size term from the strongest candidates."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and 9 <= len(request.prompt_token_ids) <= 10)",
        "name": "early_short_prompt",
        "rationale": "Provides a shared indicator for both elevated short-prompt states."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and len(request.prompt_token_ids) == 10)",
        "name": "ten_token_prompt",
        "rationale": "Allows an independently fitted increment for the highest-cost state."
      },
      {
        "expression": "int(request.prompt_token_ids is not None and 12 <= len(request.prompt_token_ids) < 23)",
        "name": "medium_prompt",
        "rationale": "Restores the flat medium-prompt regime."
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
        "early_short_prompt": 15957.065943012212,
        "medium_prompt": 3456.02052464948,
        "prompt_tokens": 8.645952057892355,
        "ten_token_prompt": 15811.020217096328
      },
      "constant": 44420.21595375396,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 96.91030906327069,
    "max_unexplained_share": 0.10138771710354057,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "early_short_prompt",
      "ten_token_prompt",
      "medium_prompt"
    ],
    "raw_files": [
      "run.2296350.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 68746.0,
        "state": {
          "early_short_prompt": 1,
          "medium_prompt": 0,
          "prompt_tokens": 9,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 6970.0,
        "unexplained_share": 0.10138771710354057
      },
      {
        "calls": 1,
        "instructions_per_call": 86086.0,
        "state": {
          "early_short_prompt": 1,
          "medium_prompt": 0,
          "prompt_tokens": 10,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 8128.0,
        "unexplained_share": 0.09441721069628047
      },
      {
        "calls": 1,
        "instructions_per_call": 46371.0,
        "state": {
          "early_short_prompt": 0,
          "medium_prompt": 0,
          "prompt_tokens": 11,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 2958.0,
        "unexplained_share": 0.06378986866791744
      },
      {
        "calls": 4,
        "instructions_per_call": 51261.25,
        "state": {
          "early_short_prompt": 0,
          "medium_prompt": 1,
          "prompt_tokens": 21,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4022.0,
        "unexplained_share": 0.07846082567241337
      },
      {
        "calls": 3,
        "instructions_per_call": 54378.333333333336,
        "state": {
          "early_short_prompt": 0,
          "medium_prompt": 1,
          "prompt_tokens": 22,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4821.333333333333,
        "unexplained_share": 0.08866276396849235
      },
      {
        "calls": 10,
        "instructions_per_call": 46702.4,
        "state": {
          "early_short_prompt": 0,
          "medium_prompt": 0,
          "prompt_tokens": 45,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 2942.6,
        "unexplained_share": 0.06300746856692589
      },
      {
        "calls": 12,
        "instructions_per_call": 47723.666666666664,
        "state": {
          "early_short_prompt": 0,
          "medium_prompt": 0,
          "prompt_tokens": 46,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3252.5,
        "unexplained_share": 0.06815276836789573
      },
      {
        "calls": 4,
        "instructions_per_call": 46650.0,
        "state": {
          "early_short_prompt": 0,
          "medium_prompt": 0,
          "prompt_tokens": 47,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3001.0,
        "unexplained_share": 0.06433011789924974
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 10.138771710354057,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 10.138771710354057,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}