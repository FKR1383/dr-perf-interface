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

This is iteration 4. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "An explicit constant feature may explain the persistent fixed-work residual that remained within both allocation paths. Request-table occupancy may additionally explain variation during early allocations.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "1",
        "name": "fixed_work",
        "rationale": "Provides an explicit basis for fixed bookkeeping and call overhead across internal execution paths."
      },
      {
        "expression": "int(request.num_computed_tokens == 0)",
        "name": "initial_allocation",
        "rationale": "Separates initial allocation from the substantially cheaper decoding path."
      },
      {
        "expression": "num_new_tokens",
        "name": "new_tokens",
        "rationale": "Captures token-dependent work and distinguishes observed prompt sizes."
      },
      {
        "expression": "len(self.coordinator.single_type_managers[0].req_to_blocks)",
        "name": "active_request_tables",
        "rationale": "Captures request-table occupancy, which can affect dictionary insertion and allocation bookkeeping."
      }
    ]
  },
  "case_id": "vllm-006",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 88,
    "case": "vllm-006",
    "distinct_states": 34,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_request_tables": 0.0,
        "fixed_work": 0.0,
        "initial_allocation": 13338.997531242683,
        "new_tokens": 0.0
      },
      "constant": 40710.60880246902,
      "dependent_columns": [
        0
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 140.35551634943113,
    "max_unexplained_share": 0.501102347887356,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "fixed_work",
      "initial_allocation",
      "new_tokens",
      "active_request_tables"
    ],
    "raw_files": [
      "run.2218897.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 44996.4,
        "state": {
          "active_request_tables": 1,
          "fixed_work": 1,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 12059.200000000004,
        "unexplained_share": 0.2680036625152235
      },
      {
        "calls": 14,
        "instructions_per_call": 45326.5,
        "state": {
          "active_request_tables": 2,
          "fixed_work": 1,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 12313.214285714283,
        "unexplained_share": 0.2716559691508121
      },
      {
        "calls": 9,
        "instructions_per_call": 44993.666666666664,
        "state": {
          "active_request_tables": 3,
          "fixed_work": 1,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 12014.888888888887,
        "unexplained_share": 0.2670351135838871
      },
      {
        "calls": 8,
        "instructions_per_call": 44959.375,
        "state": {
          "active_request_tables": 4,
          "fixed_work": 1,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 12006.375,
        "unexplained_share": 0.2670494196149302
      },
      {
        "calls": 10,
        "instructions_per_call": 45035.3,
        "state": {
          "active_request_tables": 5,
          "fixed_work": 1,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 12046.1,
        "unexplained_share": 0.2674812869016083
      },
      {
        "calls": 6,
        "instructions_per_call": 44944.666666666664,
        "state": {
          "active_request_tables": 6,
          "fixed_work": 1,
          "initial_allocation": 0,
          "new_tokens": 1
        },
        "unexplained_instructions_per_call": 11967.0,
        "unexplained_share": 0.2662607354228162
      },
      {
        "calls": 1,
        "instructions_per_call": 75785.0,
        "state": {
          "active_request_tables": 1,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 9
        },
        "unexplained_instructions_per_call": 20302.0,
        "unexplained_share": 0.2678894240285017
      },
      {
        "calls": 1,
        "instructions_per_call": 131991.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 10
        },
        "unexplained_instructions_per_call": 66141.0,
        "unexplained_share": 0.501102347887356
      },
      {
        "calls": 1,
        "instructions_per_call": 101249.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 11
        },
        "unexplained_instructions_per_call": 41620.0,
        "unexplained_share": 0.411065788304082
      },
      {
        "calls": 1,
        "instructions_per_call": 73083.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 21
        },
        "unexplained_instructions_per_call": 18587.0,
        "unexplained_share": 0.25432727173214015
      },
      {
        "calls": 1,
        "instructions_per_call": 74772.0,
        "state": {
          "active_request_tables": 1,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 21
        },
        "unexplained_instructions_per_call": 19512.0,
        "unexplained_share": 0.26095329802599904
      },
      {
        "calls": 1,
        "instructions_per_call": 74196.0,
        "state": {
          "active_request_tables": 2,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 21
        },
        "unexplained_instructions_per_call": 18922.0,
        "unexplained_share": 0.2550272251873416
      },
      {
        "calls": 1,
        "instructions_per_call": 74511.0,
        "state": {
          "active_request_tables": 3,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 21
        },
        "unexplained_instructions_per_call": 19211.0,
        "unexplained_share": 0.25782770329213134
      },
      {
        "calls": 1,
        "instructions_per_call": 73365.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 22
        },
        "unexplained_instructions_per_call": 18747.0,
        "unexplained_share": 0.25553056634635046
      },
      {
        "calls": 1,
        "instructions_per_call": 75464.0,
        "state": {
          "active_request_tables": 1,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 22
        },
        "unexplained_instructions_per_call": 19984.0,
        "unexplained_share": 0.26481501113113537
      },
      {
        "calls": 1,
        "instructions_per_call": 74449.0,
        "state": {
          "active_request_tables": 2,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 22
        },
        "unexplained_instructions_per_call": 18941.0,
        "unexplained_share": 0.25441577455707937
      },
      {
        "calls": 1,
        "instructions_per_call": 73057.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 18551.0,
        "unexplained_share": 0.2539250174521264
      },
      {
        "calls": 2,
        "instructions_per_call": 74145.5,
        "state": {
          "active_request_tables": 1,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 18865.0,
        "unexplained_share": 0.2544321637860693
      },
      {
        "calls": 1,
        "instructions_per_call": 73895.0,
        "state": {
          "active_request_tables": 2,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 18726.0,
        "unexplained_share": 0.2534136274443467
      },
      {
        "calls": 1,
        "instructions_per_call": 74499.0,
        "state": {
          "active_request_tables": 3,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 19191.0,
        "unexplained_share": 0.25760077316474045
      },
      {
        "calls": 2,
        "instructions_per_call": 74064.5,
        "state": {
          "active_request_tables": 4,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 18847.5,
        "unexplained_share": 0.25447414078269615
      },
      {
        "calls": 2,
        "instructions_per_call": 74180.5,
        "state": {
          "active_request_tables": 5,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 18807.5,
        "unexplained_share": 0.25353698074291764
      },
      {
        "calls": 1,
        "instructions_per_call": 73979.0,
        "state": {
          "active_request_tables": 7,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 45
        },
        "unexplained_instructions_per_call": 18774.0,
        "unexplained_share": 0.25377471985293126
      },
      {
        "calls": 2,
        "instructions_per_call": 73284.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 18703.5,
        "unexplained_share": 0.2552194203373178
      },
      {
        "calls": 2,
        "instructions_per_call": 74239.5,
        "state": {
          "active_request_tables": 1,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 18955.0,
        "unexplained_share": 0.2553223014702416
      },
      {
        "calls": 2,
        "instructions_per_call": 74459.5,
        "state": {
          "active_request_tables": 2,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 19168.5,
        "unexplained_share": 0.2574352500352541
      },
      {
        "calls": 2,
        "instructions_per_call": 74219.0,
        "state": {
          "active_request_tables": 3,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 18860.5,
        "unexplained_share": 0.2541195650709387
      },
      {
        "calls": 2,
        "instructions_per_call": 74279.5,
        "state": {
          "active_request_tables": 4,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 18893.0,
        "unexplained_share": 0.2543501235199483
      },
      {
        "calls": 1,
        "instructions_per_call": 74220.0,
        "state": {
          "active_request_tables": 5,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 18981.0,
        "unexplained_share": 0.25573969280517383
      },
      {
        "calls": 1,
        "instructions_per_call": 74043.0,
        "state": {
          "active_request_tables": 6,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 46
        },
        "unexplained_instructions_per_call": 18844.0,
        "unexplained_share": 0.2545007630701079
      },
      {
        "calls": 1,
        "instructions_per_call": 73425.0,
        "state": {
          "active_request_tables": 0,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 47
        },
        "unexplained_instructions_per_call": 18812.0,
        "unexplained_share": 0.2562070139598229
      },
      {
        "calls": 1,
        "instructions_per_call": 74096.0,
        "state": {
          "active_request_tables": 2,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 47
        },
        "unexplained_instructions_per_call": 18878.0,
        "unexplained_share": 0.254777585834593
      },
      {
        "calls": 1,
        "instructions_per_call": 74369.0,
        "state": {
          "active_request_tables": 3,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 47
        },
        "unexplained_instructions_per_call": 18892.0,
        "unexplained_share": 0.2540305772566526
      },
      {
        "calls": 1,
        "instructions_per_call": 73974.0,
        "state": {
          "active_request_tables": 6,
          "fixed_work": 1,
          "initial_allocation": 1,
          "new_tokens": 47
        },
        "unexplained_instructions_per_call": 18774.0,
        "unexplained_share": 0.25379187282018006
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "cd8431f9c844bce8867d4cb27e203f229e5dadc4fb6f98790440f14218aa0995",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 50.110234788735596,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 50.110234788735596,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "cd8431f9c844bce8867d4cb27e203f229e5dadc4fb6f98790440f14218aa0995"
  }
}