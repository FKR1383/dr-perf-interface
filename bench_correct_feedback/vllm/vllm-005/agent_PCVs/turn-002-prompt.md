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
    "hypothesis": "Instruction count is approximately a fixed entry cost plus a linear cost per newly cached block; block size does not drive token processing on this workload's event-disabled path.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "max(0, num_full_blocks - num_cached_blocks)",
        "name": "new_block_count",
        "rationale": "Counts loop iterations and newly inserted cache entries. In the fixed workload every block is non-null, unmasked, and initially unhashed, with cache events disabled."
      }
    ]
  },
  "case_id": "vllm-005",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 12,
    "case": "vllm-005",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "new_block_count": 7396.870629370637
      },
      "constant": 7878.007575757578,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 12.60860095685348,
    "max_unexplained_share": 0.19569344755730494,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "new_block_count"
    ],
    "raw_files": [
      "run.1802149.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 21595.0,
        "state": {
          "new_block_count": 1
        },
        "unexplained_instructions_per_call": 4226.0,
        "unexplained_share": 0.19569344755730494
      },
      {
        "calls": 1,
        "instructions_per_call": 27884.0,
        "state": {
          "new_block_count": 2
        },
        "unexplained_instructions_per_call": 3936.0,
        "unexplained_share": 0.14115621861999714
      },
      {
        "calls": 1,
        "instructions_per_call": 29321.0,
        "state": {
          "new_block_count": 3
        },
        "unexplained_instructions_per_call": 1025.0,
        "unexplained_share": 0.03495788001773473
      },
      {
        "calls": 1,
        "instructions_per_call": 36812.0,
        "state": {
          "new_block_count": 4
        },
        "unexplained_instructions_per_call": 1082.0,
        "unexplained_share": 0.029392589373030534
      },
      {
        "calls": 1,
        "instructions_per_call": 45290.0,
        "state": {
          "new_block_count": 5
        },
        "unexplained_instructions_per_call": 1536.0,
        "unexplained_share": 0.03391477147273129
      },
      {
        "calls": 1,
        "instructions_per_call": 52973.0,
        "state": {
          "new_block_count": 6
        },
        "unexplained_instructions_per_call": 1674.0,
        "unexplained_share": 0.03160100428520189
      },
      {
        "calls": 1,
        "instructions_per_call": 61673.0,
        "state": {
          "new_block_count": 7
        },
        "unexplained_instructions_per_call": 2170.0,
        "unexplained_share": 0.03518557553548554
      },
      {
        "calls": 1,
        "instructions_per_call": 69322.0,
        "state": {
          "new_block_count": 8
        },
        "unexplained_instructions_per_call": 2383.0,
        "unexplained_share": 0.03437581143071464
      },
      {
        "calls": 1,
        "instructions_per_call": 76392.0,
        "state": {
          "new_block_count": 9
        },
        "unexplained_instructions_per_call": 2289.0,
        "unexplained_share": 0.029963870562362552
      },
      {
        "calls": 1,
        "instructions_per_call": 84598.0,
        "state": {
          "new_block_count": 10
        },
        "unexplained_instructions_per_call": 2546.0,
        "unexplained_share": 0.030095274119955554
      },
      {
        "calls": 1,
        "instructions_per_call": 93624.0,
        "state": {
          "new_block_count": 11
        },
        "unexplained_instructions_per_call": 3042.0,
        "unexplained_share": 0.032491668802871056
      },
      {
        "calls": 1,
        "instructions_per_call": 101442.0,
        "state": {
          "new_block_count": 12
        },
        "unexplained_instructions_per_call": 3525.0,
        "unexplained_share": 0.03474892056544626
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "638f94e41943f192895fbd17e68d72344bfefef27c9fd71609f26fbba5d7b04a",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 19.569344755730494,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 19.569344755730494,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "638f94e41943f192895fbd17e68d72344bfefef27c9fd71609f26fbba5d7b04a"
  }
}