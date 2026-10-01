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
    "hypothesis": "The previous measurements show only zero or one allocated block and no full-block caching or prefix reuse. Initial-allocation overhead is therefore the main cost driver; token counts should expose enough distinct entry states to evaluate residual variation within the two observed paths.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "int(request.num_computed_tokens == 0)",
        "name": "initial_allocation",
        "rationale": "Captures the observed cost difference between initial allocation and incremental decoding."
      },
      {
        "expression": "num_new_tokens",
        "name": "new_tokens",
        "rationale": "Distinguishes prompt sizes and measures any token-dependent work during allocation."
      },
      {
        "expression": "request.num_computed_tokens",
        "name": "computed_tokens",
        "rationale": "Distinguishes decoding positions and captures work depending on the existing computed prefix."
      }
    ]
  },
  "case_id": "vllm-006",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 88,
    "case": "vllm-006",
    "distinct_states": 19,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "computed_tokens": 0.0,
        "initial_allocation": 14342.2468553357,
        "new_tokens": -7.018142280211244
      },
      "constant": 38958.34799946467,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 107.13259778311476,
    "max_unexplained_share": 0.46624265405707555,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "initial_allocation",
      "new_tokens",
      "computed_tokens"
    ],
    "raw_files": [
      "run.2218064.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 46600.0,
        "state": {
          "computed_tokens": 9,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 12085.0,
        "unexplained_share": 0.25933476394849786
      },
      {
        "calls": 1,
        "instructions_per_call": 47959.0,
        "state": {
          "computed_tokens": 11,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 13010.0,
        "unexplained_share": 0.27127337934485707
      },
      {
        "calls": 1,
        "instructions_per_call": 45015.0,
        "state": {
          "computed_tokens": 12,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10893.0,
        "unexplained_share": 0.24198600466511164
      },
      {
        "calls": 3,
        "instructions_per_call": 45075.0,
        "state": {
          "computed_tokens": 21,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10869.0,
        "unexplained_share": 0.2411314475873544
      },
      {
        "calls": 4,
        "instructions_per_call": 44912.5,
        "state": {
          "computed_tokens": 22,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10762.5,
        "unexplained_share": 0.23963261898135263
      },
      {
        "calls": 3,
        "instructions_per_call": 45343.333333333336,
        "state": {
          "computed_tokens": 23,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 11123.333333333334,
        "unexplained_share": 0.2453135337793134
      },
      {
        "calls": 1,
        "instructions_per_call": 44956.0,
        "state": {
          "computed_tokens": 24,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10845.0,
        "unexplained_share": 0.2412358750778539
      },
      {
        "calls": 9,
        "instructions_per_call": 45066.0,
        "state": {
          "computed_tokens": 45,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10864.888888888889,
        "unexplained_share": 0.2410883790194135
      },
      {
        "calls": 13,
        "instructions_per_call": 45208.61538461538,
        "state": {
          "computed_tokens": 46,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10980.538461538463,
        "unexplained_share": 0.242885971360122
      },
      {
        "calls": 11,
        "instructions_per_call": 44999.454545454544,
        "state": {
          "computed_tokens": 47,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10844.0,
        "unexplained_share": 0.24098069875594452
      },
      {
        "calls": 5,
        "instructions_per_call": 44983.4,
        "state": {
          "computed_tokens": 48,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 10839.599999999999,
        "unexplained_share": 0.24096889074636418
      },
      {
        "calls": 1,
        "instructions_per_call": 75927.0,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 9
        },
        "unexplained_instructions_per_call": 18542.0,
        "unexplained_share": 0.2442082526637428
      },
      {
        "calls": 1,
        "instructions_per_call": 132386.0,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 10
        },
        "unexplained_instructions_per_call": 61724.0,
        "unexplained_share": 0.46624265405707555
      },
      {
        "calls": 1,
        "instructions_per_call": 101619.0,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 11
        },
        "unexplained_instructions_per_call": 38725.0,
        "unexplained_share": 0.3810803097845875
      },
      {
        "calls": 4,
        "instructions_per_call": 74052.25,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 21
        },
        "unexplained_instructions_per_call": 17085.25,
        "unexplained_share": 0.23071885054134075
      },
      {
        "calls": 3,
        "instructions_per_call": 74642.66666666667,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 22
        },
        "unexplained_instructions_per_call": 17413.999999999996,
        "unexplained_share": 0.23329820299381937
      },
      {
        "calls": 10,
        "instructions_per_call": 74053.6,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 16949.4,
        "unexplained_share": 0.22888016247690862
      },
      {
        "calls": 12,
        "instructions_per_call": 74173.0,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 17094.500000000004,
        "unexplained_share": 0.23046796003936748
      },
      {
        "calls": 4,
        "instructions_per_call": 73987.0,
        "state": {
          "computed_tokens": 0,
          "initial_allocation": 1,
          "new_tokens": 47
        },
        "unexplained_instructions_per_call": 16919.25,
        "unexplained_share": 0.22867868679632908
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "cd8431f9c844bce8867d4cb27e203f229e5dadc4fb6f98790440f14218aa0995",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 46.624265405707554,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 46.624265405707554,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "cd8431f9c844bce8867d4cb27e203f229e5dadc4fb6f98790440f14218aa0995"
  }
}