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
    "hypothesis": "The workload adds new requests to a priority queue; insertion depth and incoming priority should explain its main instruction-count variation.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(self.waiting)",
        "name": "waiting_depth",
        "rationale": "Queue size captures variation in priority-queue insertion and allocation costs."
      },
      {
        "expression": "0 if len(self.waiting) == 0 else 1 if len(self.waiting) < 3 else 2 if len(self.waiting) < 7 else 3",
        "name": "heap_height",
        "rationale": "Gives the maximum sift-up distance for the fixed workload's queue sizes of zero through seven."
      },
      {
        "expression": "request.priority",
        "name": "incoming_priority",
        "rationale": "Incoming priority influences comparisons and movement during heap insertion."
      }
    ]
  },
  "case_id": "vllm-030",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-030",
    "distinct_states": 30,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "heap_height": 333.86141455682656,
        "incoming_priority": 0.0,
        "waiting_depth": -13.15324508417942
      },
      "constant": 7278.748053663474,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 131.02971310494468,
    "max_unexplained_share": 0.17086371158921143,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "waiting_depth",
      "heap_height",
      "incoming_priority"
    ],
    "raw_files": [
      "run.2254621.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 6681.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 0,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.06331387516838796
      },
      {
        "calls": 2,
        "instructions_per_call": 11178.5,
        "state": {
          "heap_height": 0,
          "incoming_priority": 1,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 1910.0,
        "unexplained_share": 0.17086371158921143
      },
      {
        "calls": 2,
        "instructions_per_call": 9582.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 2,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 1431.5,
        "unexplained_share": 0.14939469839281988
      },
      {
        "calls": 2,
        "instructions_per_call": 8007.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 3,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 855.0,
        "unexplained_share": 0.10678156612963657
      },
      {
        "calls": 1,
        "instructions_per_call": 6647.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 4,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.0636377313073567
      },
      {
        "calls": 1,
        "instructions_per_call": 7815.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 0,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 483.0,
        "unexplained_share": 0.0618042226487524
      },
      {
        "calls": 2,
        "instructions_per_call": 8336.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 1,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 667.0,
        "unexplained_share": 0.08001439539347409
      },
      {
        "calls": 2,
        "instructions_per_call": 8758.5,
        "state": {
          "heap_height": 1,
          "incoming_priority": 2,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 848.0,
        "unexplained_share": 0.09682023177484729
      },
      {
        "calls": 1,
        "instructions_per_call": 7805.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 3,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 483.0,
        "unexplained_share": 0.06188340807174888
      },
      {
        "calls": 1,
        "instructions_per_call": 8258.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 4,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 591.0,
        "unexplained_share": 0.07156696536691692
      },
      {
        "calls": 1,
        "instructions_per_call": 7656.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 0,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05525078369905956
      },
      {
        "calls": 2,
        "instructions_per_call": 7827.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 1,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.0540436949022614
      },
      {
        "calls": 1,
        "instructions_per_call": 8339.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 2,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 521.0,
        "unexplained_share": 0.06247751528960307
      },
      {
        "calls": 1,
        "instructions_per_call": 7620.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 3,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05551181102362205
      },
      {
        "calls": 1,
        "instructions_per_call": 7680.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 4,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.055078125
      },
      {
        "calls": 1,
        "instructions_per_call": 9127.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 0,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.046346006354771555
      },
      {
        "calls": 1,
        "instructions_per_call": 8695.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.04864864864864865
      },
      {
        "calls": 1,
        "instructions_per_call": 9072.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.04662698412698413
      },
      {
        "calls": 1,
        "instructions_per_call": 7630.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 3,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05543905635648755
      },
      {
        "calls": 1,
        "instructions_per_call": 7742.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 4,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05463704469129424
      },
      {
        "calls": 1,
        "instructions_per_call": 8926.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.047389648218686985
      },
      {
        "calls": 1,
        "instructions_per_call": 7873.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.0537279309030865
      },
      {
        "calls": 1,
        "instructions_per_call": 8302.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 3,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05095157793302819
      },
      {
        "calls": 1,
        "instructions_per_call": 7863.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 4,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05379626096909577
      },
      {
        "calls": 1,
        "instructions_per_call": 9117.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "waiting_depth": 5
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.04639684106614018
      },
      {
        "calls": 1,
        "instructions_per_call": 7985.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "waiting_depth": 5
        },
        "unexplained_instructions_per_call": 531.0,
        "unexplained_share": 0.0664996869129618
      },
      {
        "calls": 1,
        "instructions_per_call": 7674.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 3,
          "waiting_depth": 5
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.055121188428459734
      },
      {
        "calls": 1,
        "instructions_per_call": 9178.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "waiting_depth": 6
        },
        "unexplained_instructions_per_call": 955.0,
        "unexplained_share": 0.10405317062540859
      },
      {
        "calls": 1,
        "instructions_per_call": 7823.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "waiting_depth": 6
        },
        "unexplained_instructions_per_call": 423.0,
        "unexplained_share": 0.05407132813498658
      },
      {
        "calls": 1,
        "instructions_per_call": 9142.0,
        "state": {
          "heap_height": 3,
          "incoming_priority": 1,
          "waiting_depth": 7
        },
        "unexplained_instructions_per_call": 451.0,
        "unexplained_share": 0.04933274994530737
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8eb6d70fe60623b2729daa842cd8e42e6a6b7fe234f8ebf98236010cbf25c786",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.086371158921143,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.086371158921143,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8eb6d70fe60623b2729daa842cd8e42e6a6b7fe234f8ebf98236010cbf25c786"
  }
}