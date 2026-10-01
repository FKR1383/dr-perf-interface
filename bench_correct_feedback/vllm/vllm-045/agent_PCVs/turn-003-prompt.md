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
    "hypothesis": "Admission cost combines fixed overhead, prompt-size-dependent work, initial task discovery, and sampling-mode-dependent processing.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0",
        "name": "prompt_tokens",
        "rationale": "Captures token-dependent validation, detokenizer initialization, and request construction."
      },
      {
        "expression": "len(prompt_text or '') if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt', '') or '') if isinstance(prompt, dict) else len(prompt) if isinstance(prompt, str) else 0",
        "name": "prompt_characters",
        "rationale": "Captures processing proportional to prompt text size."
      },
      {
        "expression": "int('_supported_tasks' not in self.__dict__)",
        "name": "supported_tasks_uncached",
        "rationale": "Distinguishes initial supported-task discovery and first-request overhead."
      },
      {
        "expression": "int(isinstance(params, SamplingParams) and params.temperature == 0)",
        "name": "greedy_sampling",
        "rationale": "Separates greedy and stochastic sampling parameter processing."
      }
    ]
  },
  "case_id": "vllm-045",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-045",
    "distinct_states": 13,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "greedy_sampling": 423.0,
        "prompt_characters": -1224.7722315384,
        "prompt_tokens": 3943.2470999972566,
        "supported_tasks_uncached": 0.0
      },
      "constant": 68657.93579211734,
      "dependent_columns": [
        2
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 122.48852611798793,
    "max_unexplained_share": 0.9974054429761641,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "prompt_characters",
      "supported_tasks_uncached",
      "greedy_sampling"
    ],
    "raw_files": [
      "run.2307969.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 630668.0,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 21,
          "prompt_tokens": 9,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 574440.0,
        "unexplained_share": 0.9108437402880755
      },
      {
        "calls": 1,
        "instructions_per_call": 48680757.0,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 21,
          "prompt_tokens": 10,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 48554452.0,
        "unexplained_share": 0.9974054429761641
      },
      {
        "calls": 1,
        "instructions_per_call": 535327.0,
        "state": {
          "greedy_sampling": 0,
          "prompt_characters": 33,
          "prompt_tokens": 11,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 486278.0,
        "unexplained_share": 0.9083756283542582
      },
      {
        "calls": 1,
        "instructions_per_call": 545127.0,
        "state": {
          "greedy_sampling": 0,
          "prompt_characters": 83,
          "prompt_tokens": 21,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 493846.0,
        "unexplained_share": 0.905928343303487
      },
      {
        "calls": 3,
        "instructions_per_call": 550310.6666666666,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 83,
          "prompt_tokens": 21,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 498626.0000000001,
        "unexplained_share": 0.9060809288329261
      },
      {
        "calls": 1,
        "instructions_per_call": 570774.0,
        "state": {
          "greedy_sampling": 0,
          "prompt_characters": 83,
          "prompt_tokens": 22,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 518733.0,
        "unexplained_share": 0.9088238076716879
      },
      {
        "calls": 2,
        "instructions_per_call": 555759.0,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 83,
          "prompt_tokens": 22,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 502873.0,
        "unexplained_share": 0.9048400475745781
      },
      {
        "calls": 3,
        "instructions_per_call": 551953.0,
        "state": {
          "greedy_sampling": 0,
          "prompt_characters": 156,
          "prompt_tokens": 45,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 495628.3333333332,
        "unexplained_share": 0.8979538716762717
      },
      {
        "calls": 7,
        "instructions_per_call": 550510.0,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 156,
          "prompt_tokens": 45,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 493626.4285714287,
        "unexplained_share": 0.896671138710339
      },
      {
        "calls": 4,
        "instructions_per_call": 557705.75,
        "state": {
          "greedy_sampling": 0,
          "prompt_characters": 156,
          "prompt_tokens": 46,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 500515.0,
        "unexplained_share": 0.8974535406887951
      },
      {
        "calls": 8,
        "instructions_per_call": 553931.5,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 156,
          "prompt_tokens": 46,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 496650.0,
        "unexplained_share": 0.8965910044834063
      },
      {
        "calls": 2,
        "instructions_per_call": 548156.5,
        "state": {
          "greedy_sampling": 0,
          "prompt_characters": 162,
          "prompt_tokens": 47,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 491225.5,
        "unexplained_share": 0.8961409743385329
      },
      {
        "calls": 2,
        "instructions_per_call": 551327.0,
        "state": {
          "greedy_sampling": 1,
          "prompt_characters": 162,
          "prompt_tokens": 47,
          "supported_tasks_uncached": 0
        },
        "unexplained_instructions_per_call": 493712.5,
        "unexplained_share": 0.8954984972620604
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 99.74054429761641,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 99.74054429761641,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}