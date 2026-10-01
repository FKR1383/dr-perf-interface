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

This is iteration 7. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The fitted prompt-length slope is small. Replacing it with scheduler request cardinality may explain batch-position variation that length-only models leave unresolved, while retaining the observed startup and medium-prompt regimes.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "len(self.scheduler.requests)",
        "name": "resident_requests",
        "rationale": "Exposes request population at entry, distinguishing positions within each submitted batch and possible batch-start effects."
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
        "expression": "int(request.prompt_token_ids is not None and 12 <= len(request.prompt_token_ids) < 23)",
        "name": "medium_prompt",
        "rationale": "Retains the medium-prompt regime from the best-performing candidate."
      }
    ]
  },
  "case_id": "vllm-042",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-042",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "medium_prompt": 1755.2484929078016,
        "nine_token_prompt": 10310.060771276596,
        "resident_requests": 61.77393617021278,
        "ten_token_prompt": 24868.594547872333
      },
      "constant": 40772.394300911874,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 103.67148920614272,
    "max_unexplained_share": 0.21833113359730166,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "resident_requests",
      "nine_token_prompt",
      "ten_token_prompt",
      "medium_prompt"
    ],
    "raw_files": [
      "run.2293744.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 46825.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 0,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 5263.0,
        "unexplained_share": 0.11239722370528564
      },
      {
        "calls": 2,
        "instructions_per_call": 54232.5,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "resident_requests": 0,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 9728.5,
        "unexplained_share": 0.1793850550868944
      },
      {
        "calls": 1,
        "instructions_per_call": 85462.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 0,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 18385.0,
        "unexplained_share": 0.2151248508108867
      },
      {
        "calls": 1,
        "instructions_per_call": 68190.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 1,
          "resident_requests": 0,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 14888.0,
        "unexplained_share": 0.21833113359730166
      },
      {
        "calls": 5,
        "instructions_per_call": 46053.4,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 1,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 5602.000000000002,
        "unexplained_share": 0.12164139889780129
      },
      {
        "calls": 2,
        "instructions_per_call": 52174.5,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "resident_requests": 1,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 9021.5,
        "unexplained_share": 0.17291013809427977
      },
      {
        "calls": 4,
        "instructions_per_call": 42902.75,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 2,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 3397.25,
        "unexplained_share": 0.07918490073480139
      },
      {
        "calls": 2,
        "instructions_per_call": 49716.0,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "resident_requests": 2,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7601.0,
        "unexplained_share": 0.15288840614691449
      },
      {
        "calls": 4,
        "instructions_per_call": 44671.5,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 3,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 4806.75,
        "unexplained_share": 0.10760216245257043
      },
      {
        "calls": 1,
        "instructions_per_call": 49315.0,
        "state": {
          "medium_prompt": 1,
          "nine_token_prompt": 0,
          "resident_requests": 3,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7295.0,
        "unexplained_share": 0.14792659434249214
      },
      {
        "calls": 4,
        "instructions_per_call": 46269.5,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 4,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 6067.0,
        "unexplained_share": 0.1311230940468343
      },
      {
        "calls": 3,
        "instructions_per_call": 48103.666666666664,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 5,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 7146.333333333333,
        "unexplained_share": 0.14856109374891727
      },
      {
        "calls": 2,
        "instructions_per_call": 46284.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 6,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 6027.0,
        "unexplained_share": 0.13021778584392016
      },
      {
        "calls": 1,
        "instructions_per_call": 46147.0,
        "state": {
          "medium_prompt": 0,
          "nine_token_prompt": 0,
          "resident_requests": 7,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 6005.0,
        "unexplained_share": 0.13012763559928056
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 21.833113359730167,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 21.833113359730167,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}