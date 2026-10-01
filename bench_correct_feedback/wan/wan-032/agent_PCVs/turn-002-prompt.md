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
    "hypothesis": "Instruction count is approximately linear in the number of prompts, total characters, and whitespace substitutions.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(prompt)",
        "name": "prompt_count",
        "rationale": "Captures per-string cleaning calls and list construction overhead."
      },
      {
        "expression": "sum((len(u) for u in prompt))",
        "name": "total_characters",
        "rationale": "Captures length-dependent scanning in text repair, HTML unescaping, and whitespace normalization."
      },
      {
        "expression": "sum((u.count(' ') for u in prompt))",
        "name": "space_count",
        "rationale": "Captures whitespace matches and substitutions for the supplied ASCII prompts."
      }
    ]
  },
  "case_id": "wan-032",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-032",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "prompt_count": 4253.090249798548,
        "space_count": 1509.2557077625497,
        "total_characters": -254.60878323931917
      },
      "constant": 29967.400172911377,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 13.35319388937205,
    "max_unexplained_share": 0.6816837062608087,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_count",
      "total_characters",
      "space_count"
    ],
    "raw_files": [
      "run.1584402.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 12,
        "instructions_per_call": 50408.833333333336,
        "state": {
          "prompt_count": 1,
          "space_count": 0,
          "total_characters": 4
        },
        "unexplained_instructions_per_call": 32119.416666666668,
        "unexplained_share": 0.637178338452586
      },
      {
        "calls": 3,
        "instructions_per_call": 201230.66666666666,
        "state": {
          "prompt_count": 1,
          "space_count": 1,
          "total_characters": 8
        },
        "unexplained_instructions_per_call": 137175.6666666667,
        "unexplained_share": 0.6816837062608087
      },
      {
        "calls": 3,
        "instructions_per_call": 56292.666666666664,
        "state": {
          "prompt_count": 1,
          "space_count": 2,
          "total_characters": 13
        },
        "unexplained_instructions_per_call": 32220.333333333332,
        "unexplained_share": 0.5723717713378889
      },
      {
        "calls": 3,
        "instructions_per_call": 56359.666666666664,
        "state": {
          "prompt_count": 1,
          "space_count": 2,
          "total_characters": 14
        },
        "unexplained_instructions_per_call": 32220.333333333332,
        "unexplained_share": 0.571691339551334
      },
      {
        "calls": 3,
        "instructions_per_call": 61188.0,
        "state": {
          "prompt_count": 1,
          "space_count": 4,
          "total_characters": 21
        },
        "unexplained_instructions_per_call": 32256.333333333332,
        "unexplained_share": 0.5271676363557124
      },
      {
        "calls": 6,
        "instructions_per_call": 97400.0,
        "state": {
          "prompt_count": 2,
          "space_count": 0,
          "total_characters": 8
        },
        "unexplained_instructions_per_call": 62545.333333333336,
        "unexplained_share": 0.6421492128678987
      },
      {
        "calls": 3,
        "instructions_per_call": 104128.0,
        "state": {
          "prompt_count": 2,
          "space_count": 2,
          "total_characters": 17
        },
        "unexplained_instructions_per_call": 62691.0,
        "unexplained_share": 0.6020570835894284
      },
      {
        "calls": 3,
        "instructions_per_call": 106814.66666666667,
        "state": {
          "prompt_count": 2,
          "space_count": 3,
          "total_characters": 24
        },
        "unexplained_instructions_per_call": 62693.666666666664,
        "unexplained_share": 0.5869387474878606
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "d8e444a7f6e029976e7efb808a0ee2fe1c891b05f96c311dda65eae8a9f34b6d",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 68.16837062608087,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 68.16837062608087,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "d8e444a7f6e029976e7efb808a0ee2fe1c891b05f96c311dda65eae8a9f34b6d"
  }
}