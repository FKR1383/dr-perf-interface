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

This is iteration 3. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The initial default-options call includes substantial initialization cost. Subsequent costs depend on request count and text volume, with smaller contributions from tokenization options.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Tracks rendering and engine insertion work repeated for each request."
      },
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Separates the default-options entry state, which coincides with the unusually expensive initial call in this workload."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) * len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0])",
        "name": "prompt_character_work",
        "rationale": "Estimates batch text volume from the first prompt and batch cardinality without consuming the generator; prompts within each batch have similar lengths."
      },
      {
        "expression": "len(params) * len(prompts.gi_frame.f_locals.get('tokenization_kwargs') or {})",
        "name": "tokenization_option_work",
        "rationale": "Tracks per-request option processing."
      }
    ]
  },
  "case_id": "vllm-002",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 8,
    "case": "vllm-002",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "default_tokenization": 50979175.328634635,
        "prompt_character_work": 1715.1756759199477,
        "request_count": 563396.3552965212,
        "tokenization_option_work": 3745.5612296542677
      },
      "constant": 607567.2008098805,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 132.36279840487987,
    "max_unexplained_share": 0.2928536557931563,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "request_count",
      "default_tokenization",
      "prompt_character_work",
      "tokenization_option_work"
    ],
    "raw_files": [
      "run.1781322.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 59664891.0,
        "state": {
          "default_tokenization": 1,
          "prompt_character_work": 0,
          "request_count": 1,
          "tokenization_option_work": 0
        },
        "unexplained_instructions_per_call": 7620995.0,
        "unexplained_share": 0.12772997439985267
      },
      {
        "calls": 1,
        "instructions_per_call": 2303501.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 42,
          "request_count": 2,
          "tokenization_option_work": 2
        },
        "unexplained_instructions_per_call": 578553.0,
        "unexplained_share": 0.25116246964945965
      },
      {
        "calls": 1,
        "instructions_per_call": 3784536.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 249,
          "request_count": 3,
          "tokenization_option_work": 6
        },
        "unexplained_instructions_per_call": 1017909.0,
        "unexplained_share": 0.26896533683389456
      },
      {
        "calls": 1,
        "instructions_per_call": 4559854.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 332,
          "request_count": 4,
          "tokenization_option_work": 12
        },
        "unexplained_instructions_per_call": 1100746.0,
        "unexplained_share": 0.24139939568240562
      },
      {
        "calls": 1,
        "instructions_per_call": 6898968.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 780,
          "request_count": 5,
          "tokenization_option_work": 20
        },
        "unexplained_instructions_per_call": 2020388.0,
        "unexplained_share": 0.2928536557931563
      },
      {
        "calls": 1,
        "instructions_per_call": 7933122.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 936,
          "request_count": 6,
          "tokenization_option_work": 30
        },
        "unexplained_instructions_per_call": 2223106.0,
        "unexplained_share": 0.280230910352822
      },
      {
        "calls": 1,
        "instructions_per_call": 9255993.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 1092,
          "request_count": 7,
          "tokenization_option_work": 42
        },
        "unexplained_instructions_per_call": 2617620.0,
        "unexplained_share": 0.28280272035642207
      },
      {
        "calls": 1,
        "instructions_per_call": 10507540.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 1248,
          "request_count": 8,
          "tokenization_option_work": 56
        },
        "unexplained_instructions_per_call": 2952545.0,
        "unexplained_share": 0.2809929821823186
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 29.28536557931563,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 29.28536557931563,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}