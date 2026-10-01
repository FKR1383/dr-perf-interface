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
    "hypothesis": "A three-feature model may fit more reliably by sharing a coefficient between the two startup-associated states. Their observed excess costs are approximately proportional to this combined feature.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "len(request.prompt_token_ids) if request.prompt_token_ids is not None else 0",
        "name": "prompt_tokens",
        "rationale": "Retains the prompt-size term."
      },
      {
        "expression": "len(request.prompt_token_ids) - 8 if request.prompt_token_ids is not None and 9 <= len(request.prompt_token_ids) <= 10 else 0",
        "name": "short_prompt_regime",
        "rationale": "Combines the two elevated short-prompt states into one feature, reflecting their approximately twofold difference in excess cost."
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
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "medium_prompt": 3225.600238999789,
        "prompt_tokens": 0.994032325361788,
        "short_prompt_regime": 7298.941882425279
      },
      "constant": 38266.447881759115,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 96.69617483997717,
    "max_unexplained_share": 0.35733241375174296,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "short_prompt_regime",
      "medium_prompt"
    ],
    "raw_files": [
      "run.2295622.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 66697.0,
        "state": {
          "medium_prompt": 0,
          "prompt_tokens": 9,
          "short_prompt_regime": 1
        },
        "unexplained_instructions_per_call": 23833.0,
        "unexplained_share": 0.35733241375174296
      },
      {
        "calls": 1,
        "instructions_per_call": 84240.0,
        "state": {
          "medium_prompt": 0,
          "prompt_tokens": 10,
          "short_prompt_regime": 2
        },
        "unexplained_instructions_per_call": 27711.0,
        "unexplained_share": 0.32895299145299145
      },
      {
        "calls": 1,
        "instructions_per_call": 46007.0,
        "state": {
          "medium_prompt": 0,
          "prompt_tokens": 11,
          "short_prompt_regime": 0
        },
        "unexplained_instructions_per_call": 7754.0,
        "unexplained_share": 0.16853957006542483
      },
      {
        "calls": 4,
        "instructions_per_call": 50480.25,
        "state": {
          "medium_prompt": 1,
          "prompt_tokens": 21,
          "short_prompt_regime": 0
        },
        "unexplained_instructions_per_call": 9330.5,
        "unexplained_share": 0.18483466306129626
      },
      {
        "calls": 3,
        "instructions_per_call": 54009.666666666664,
        "state": {
          "medium_prompt": 1,
          "prompt_tokens": 22,
          "short_prompt_regime": 0
        },
        "unexplained_instructions_per_call": 11469.666666666666,
        "unexplained_share": 0.21236321892994464
      },
      {
        "calls": 10,
        "instructions_per_call": 45540.7,
        "state": {
          "medium_prompt": 0,
          "prompt_tokens": 45,
          "short_prompt_regime": 0
        },
        "unexplained_instructions_per_call": 7553.600000000001,
        "unexplained_share": 0.16586481982051224
      },
      {
        "calls": 12,
        "instructions_per_call": 46334.5,
        "state": {
          "medium_prompt": 0,
          "prompt_tokens": 46,
          "short_prompt_regime": 0
        },
        "unexplained_instructions_per_call": 8271.0,
        "unexplained_share": 0.17850629660404235
      },
      {
        "calls": 4,
        "instructions_per_call": 44532.5,
        "state": {
          "medium_prompt": 0,
          "prompt_tokens": 47,
          "short_prompt_regime": 0
        },
        "unexplained_instructions_per_call": 7229.5,
        "unexplained_share": 0.16234210969516646
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 35.733241375174295,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 35.733241375174295,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "1b8b3d9f8a6c6fcdc3494ea8a067ba9f7c094e89ccdfadcbf2ab097cea08083a"
  }
}