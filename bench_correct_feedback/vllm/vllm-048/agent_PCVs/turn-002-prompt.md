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
    "hypothesis": "The fixed workload uses cumulative output, disabled detokenization, no parent request, and stream interval one. Cost should be mostly constant, with an additional finished-request cost and potentially a small token-count contribution.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "int(finish_reason is not None)",
        "name": "finished",
        "rationale": "Captures completion-specific branches and finish-reason string conversion; the workload finishes every third request."
      },
      {
        "expression": "len(new_token_ids)",
        "name": "new_token_count",
        "rationale": "Captures any output construction cost that scales with the supplied token sequence."
      }
    ]
  },
  "case_id": "vllm-048",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 12,
    "case": "vllm-048",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "finished": 1052.9999999999998,
        "new_token_count": -6.076642335766423
      },
      "constant": 23380.331508515854,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 11.639259048737586,
    "max_unexplained_share": 0.34466677387488803,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "finished",
      "new_token_count"
    ],
    "raw_files": [
      "run.2335853.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 43529.0,
        "state": {
          "finished": 0,
          "new_token_count": 1
        },
        "unexplained_instructions_per_call": 15003.0,
        "unexplained_share": 0.34466677387488803
      },
      {
        "calls": 1,
        "instructions_per_call": 35232.0,
        "state": {
          "finished": 0,
          "new_token_count": 2
        },
        "unexplained_instructions_per_call": 10184.0,
        "unexplained_share": 0.28905540417802
      },
      {
        "calls": 1,
        "instructions_per_call": 24592.0,
        "state": {
          "finished": 0,
          "new_token_count": 4
        },
        "unexplained_instructions_per_call": 2648.0,
        "unexplained_share": 0.10767729342875731
      },
      {
        "calls": 1,
        "instructions_per_call": 25863.0,
        "state": {
          "finished": 0,
          "new_token_count": 5
        },
        "unexplained_instructions_per_call": 3326.0,
        "unexplained_share": 0.12860070370799984
      },
      {
        "calls": 1,
        "instructions_per_call": 24658.0,
        "state": {
          "finished": 0,
          "new_token_count": 7
        },
        "unexplained_instructions_per_call": 2671.0,
        "unexplained_share": 0.10832184280963582
      },
      {
        "calls": 1,
        "instructions_per_call": 24592.0,
        "state": {
          "finished": 0,
          "new_token_count": 8
        },
        "unexplained_instructions_per_call": 2648.0,
        "unexplained_share": 0.10767729342875731
      },
      {
        "calls": 1,
        "instructions_per_call": 24584.0,
        "state": {
          "finished": 0,
          "new_token_count": 10
        },
        "unexplained_instructions_per_call": 2648.0,
        "unexplained_share": 0.10771233322486169
      },
      {
        "calls": 1,
        "instructions_per_call": 24582.0,
        "state": {
          "finished": 0,
          "new_token_count": 11
        },
        "unexplained_instructions_per_call": 2648.0,
        "unexplained_share": 0.10772109673745017
      },
      {
        "calls": 1,
        "instructions_per_call": 29946.0,
        "state": {
          "finished": 1,
          "new_token_count": 3
        },
        "unexplained_instructions_per_call": 4724.0,
        "unexplained_share": 0.15775061777866828
      },
      {
        "calls": 1,
        "instructions_per_call": 28255.0,
        "state": {
          "finished": 1,
          "new_token_count": 6
        },
        "unexplained_instructions_per_call": 3814.0,
        "unexplained_share": 0.13498495841443992
      },
      {
        "calls": 1,
        "instructions_per_call": 27232.0,
        "state": {
          "finished": 1,
          "new_token_count": 9
        },
        "unexplained_instructions_per_call": 3131.0,
        "unexplained_share": 0.11497502937720329
      },
      {
        "calls": 1,
        "instructions_per_call": 28491.0,
        "state": {
          "finished": 1,
          "new_token_count": 12
        },
        "unexplained_instructions_per_call": 3809.0,
        "unexplained_share": 0.13369134112526762
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "cff3752569fb39da444bb467c2380e3851568bb416cc484d87e822a4d091ba01",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 34.4666773874888,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 34.4666773874888,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "cff3752569fb39da444bb467c2380e3851568bb416cc484d87e822a4d091ba01"
  }
}