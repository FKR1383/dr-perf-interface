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
    "hypothesis": "The largest unexplained shares occur where multiple calls share queue size and priority. Adding prompt cardinality may distinguish these heterogeneous entry states while retaining the heap-cost predictors.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(self.waiting)",
        "name": "waiting_depth",
        "rationale": "Captures queue insertion size and allocation boundaries."
      },
      {
        "expression": "0 if len(self.waiting) == 0 else 1 if len(self.waiting) < 3 else 2 if len(self.waiting) < 7 else 3",
        "name": "heap_height",
        "rationale": "Captures maximum heap insertion depth for the bounded workload."
      },
      {
        "expression": "request.priority",
        "name": "incoming_priority",
        "rationale": "Distinguishes insertion paths with different priority comparisons."
      },
      {
        "expression": "request.num_prompt_tokens",
        "name": "prompt_tokens",
        "rationale": "Separates short- and long-prompt entry states previously grouped together, testing whether their differing request construction and allocation state explains the observed variation."
      }
    ]
  },
  "case_id": "vllm-030",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-030",
    "distinct_states": 36,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "heap_height": 262.1379641794156,
        "incoming_priority": 0.0,
        "prompt_tokens": 0.0,
        "waiting_depth": -12.575348059578584
      },
      "constant": 6709.284967030837,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 121.00967470603064,
    "max_unexplained_share": 0.35536537994658896,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "waiting_depth",
      "heap_height",
      "incoming_priority",
      "prompt_tokens"
    ],
    "raw_files": [
      "run.2255562.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 6657.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 0,
          "prompt_tokens": 46,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 883.0,
        "unexplained_share": 0.13264233138050172
      },
      {
        "calls": 1,
        "instructions_per_call": 16476.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 1,
          "prompt_tokens": 10,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 5855.0,
        "unexplained_share": 0.35536537994658896
      },
      {
        "calls": 1,
        "instructions_per_call": 6657.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 1,
          "prompt_tokens": 45,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 883.0,
        "unexplained_share": 0.13264233138050172
      },
      {
        "calls": 1,
        "instructions_per_call": 12428.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 2,
          "prompt_tokens": 9,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 4027.0,
        "unexplained_share": 0.3240263920180238
      },
      {
        "calls": 1,
        "instructions_per_call": 6657.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 2,
          "prompt_tokens": 46,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 883.0,
        "unexplained_share": 0.13264233138050172
      },
      {
        "calls": 1,
        "instructions_per_call": 8607.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 3,
          "prompt_tokens": 22,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 1799.0,
        "unexplained_share": 0.2090159172766353
      },
      {
        "calls": 1,
        "instructions_per_call": 6923.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 3,
          "prompt_tokens": 45,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 964.0,
        "unexplained_share": 0.13924599162212914
      },
      {
        "calls": 1,
        "instructions_per_call": 7176.0,
        "state": {
          "heap_height": 0,
          "incoming_priority": 4,
          "prompt_tokens": 21,
          "waiting_depth": 0
        },
        "unexplained_instructions_per_call": 1153.0,
        "unexplained_share": 0.16067447045707917
      },
      {
        "calls": 1,
        "instructions_per_call": 7896.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 0,
          "prompt_tokens": 45,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 1103.0,
        "unexplained_share": 0.13969098277608916
      },
      {
        "calls": 1,
        "instructions_per_call": 8864.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 1,
          "prompt_tokens": 11,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 1649.0,
        "unexplained_share": 0.18603339350180506
      },
      {
        "calls": 1,
        "instructions_per_call": 7674.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 1,
          "prompt_tokens": 46,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 969.0,
        "unexplained_share": 0.12627052384675527
      },
      {
        "calls": 1,
        "instructions_per_call": 9258.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 2,
          "prompt_tokens": 22,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 1923.0,
        "unexplained_share": 0.20771224886584574
      },
      {
        "calls": 1,
        "instructions_per_call": 7893.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 2,
          "prompt_tokens": 47,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 1104.0,
        "unexplained_share": 0.13987077156974534
      },
      {
        "calls": 1,
        "instructions_per_call": 7650.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 3,
          "prompt_tokens": 21,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 969.0,
        "unexplained_share": 0.12666666666666668
      },
      {
        "calls": 1,
        "instructions_per_call": 8051.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 4,
          "prompt_tokens": 46,
          "waiting_depth": 1
        },
        "unexplained_instructions_per_call": 1156.0,
        "unexplained_share": 0.14358464786982983
      },
      {
        "calls": 1,
        "instructions_per_call": 7541.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 0,
          "prompt_tokens": 46,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 894.0,
        "unexplained_share": 0.11855191619148654
      },
      {
        "calls": 1,
        "instructions_per_call": 7907.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 1,
          "prompt_tokens": 22,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 894.0,
        "unexplained_share": 0.1130643733400784
      },
      {
        "calls": 1,
        "instructions_per_call": 7541.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 1,
          "prompt_tokens": 45,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 894.0,
        "unexplained_share": 0.11855191619148654
      },
      {
        "calls": 1,
        "instructions_per_call": 7477.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 2,
          "prompt_tokens": 21,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11876421024475056
      },
      {
        "calls": 1,
        "instructions_per_call": 7445.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 3,
          "prompt_tokens": 46,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11927468099395568
      },
      {
        "calls": 1,
        "instructions_per_call": 7465.0,
        "state": {
          "heap_height": 1,
          "incoming_priority": 4,
          "prompt_tokens": 45,
          "waiting_depth": 2
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11895512391158741
      },
      {
        "calls": 1,
        "instructions_per_call": 8912.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 0,
          "prompt_tokens": 47,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 964.0,
        "unexplained_share": 0.10816876122082585
      },
      {
        "calls": 1,
        "instructions_per_call": 8530.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "prompt_tokens": 21,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 964.0,
        "unexplained_share": 0.1130128956623681
      },
      {
        "calls": 1,
        "instructions_per_call": 8965.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "prompt_tokens": 46,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 970.0,
        "unexplained_share": 0.10819854991634133
      },
      {
        "calls": 1,
        "instructions_per_call": 7465.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 3,
          "prompt_tokens": 45,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11895512391158741
      },
      {
        "calls": 1,
        "instructions_per_call": 7551.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 4,
          "prompt_tokens": 46,
          "waiting_depth": 3
        },
        "unexplained_instructions_per_call": 946.0,
        "unexplained_share": 0.12528141967951265
      },
      {
        "calls": 1,
        "instructions_per_call": 8700.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "prompt_tokens": 46,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 964.0,
        "unexplained_share": 0.11080459770114942
      },
      {
        "calls": 1,
        "instructions_per_call": 7664.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "prompt_tokens": 45,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11586638830897704
      },
      {
        "calls": 1,
        "instructions_per_call": 8051.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 3,
          "prompt_tokens": 46,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11029685753322568
      },
      {
        "calls": 1,
        "instructions_per_call": 7950.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 4,
          "prompt_tokens": 45,
          "waiting_depth": 4
        },
        "unexplained_instructions_per_call": 1050.0,
        "unexplained_share": 0.1320754716981132
      },
      {
        "calls": 1,
        "instructions_per_call": 9080.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "prompt_tokens": 45,
          "waiting_depth": 5
        },
        "unexplained_instructions_per_call": 976.0,
        "unexplained_share": 0.10748898678414097
      },
      {
        "calls": 1,
        "instructions_per_call": 7810.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "prompt_tokens": 46,
          "waiting_depth": 5
        },
        "unexplained_instructions_per_call": 1069.0,
        "unexplained_share": 0.13687580025608195
      },
      {
        "calls": 1,
        "instructions_per_call": 7465.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 3,
          "prompt_tokens": 47,
          "waiting_depth": 5
        },
        "unexplained_instructions_per_call": 888.0,
        "unexplained_share": 0.11895512391158741
      },
      {
        "calls": 1,
        "instructions_per_call": 8948.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 1,
          "prompt_tokens": 46,
          "waiting_depth": 6
        },
        "unexplained_instructions_per_call": 1715.0,
        "unexplained_share": 0.1916629414394278
      },
      {
        "calls": 1,
        "instructions_per_call": 7668.0,
        "state": {
          "heap_height": 2,
          "incoming_priority": 2,
          "prompt_tokens": 45,
          "waiting_depth": 6
        },
        "unexplained_instructions_per_call": 926.0,
        "unexplained_share": 0.12076160667709963
      },
      {
        "calls": 1,
        "instructions_per_call": 8806.0,
        "state": {
          "heap_height": 3,
          "incoming_priority": 1,
          "prompt_tokens": 47,
          "waiting_depth": 7
        },
        "unexplained_instructions_per_call": 1034.0,
        "unexplained_share": 0.11741994094935271
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8eb6d70fe60623b2729daa842cd8e42e6a6b7fe234f8ebf98236010cbf25c786",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 35.53653799465889,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 35.53653799465889,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8eb6d70fe60623b2729daa842cd8e42e6a6b7fe234f8ebf98236010cbf25c786"
  }
}