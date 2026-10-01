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
    "hypothesis": "The similar unexplained instruction share across text lengths suggests runtime overhead beyond tensor dimensions. Cheap garbage-collector entry state may explain variation caused by collections during the marked region.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "prompt_embeds.shape[1]",
        "name": "text_length",
        "rationale": "Tracks text projection and cross-attention work."
      },
      {
        "expression": "int(self.scheduler.step_index is None)",
        "name": "scheduler_initialization",
        "rationale": "Separates scheduler initialization from subsequent steps."
      },
      {
        "expression": "__import__('gc').get_count()[0]",
        "name": "gc_allocation_pressure",
        "rationale": "Measures entry-state allocation pressure that can affect collection work during transformer execution."
      },
      {
        "expression": "__import__('gc').get_count()[1]",
        "name": "gc_older_generation_pressure",
        "rationale": "Tracks progress toward more costly older-generation garbage collection."
      }
    ]
  },
  "case_id": "wan-026",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 39,
    "case": "wan-026",
    "distinct_states": 30,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "gc_allocation_pressure": -332.7106139074435,
        "gc_older_generation_pressure": 3853.6504066988177,
        "scheduler_initialization": -3232.725894013908,
        "text_length": 6670.448637363843
      },
      "constant": 5620284.798212858,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 29.962039666250348,
    "max_unexplained_share": 0.3933769590858765,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "text_length",
      "scheduler_initialization",
      "gc_allocation_pressure",
      "gc_older_generation_pressure"
    ],
    "raw_files": [
      "run.1575560.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 8095632.0,
        "state": {
          "gc_allocation_pressure": 101,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 2491685.0,
        "unexplained_share": 0.3077814060718175
      },
      {
        "calls": 1,
        "instructions_per_call": 8082098.0,
        "state": {
          "gc_allocation_pressure": 138,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 2478924.0,
        "unexplained_share": 0.3067178843909094
      },
      {
        "calls": 1,
        "instructions_per_call": 8112001.0,
        "state": {
          "gc_allocation_pressure": 234,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 0,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 2508464.0,
        "unexplained_share": 0.3092287587242654
      },
      {
        "calls": 1,
        "instructions_per_call": 9378864.0,
        "state": {
          "gc_allocation_pressure": 11,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 3689429.0,
        "unexplained_share": 0.3933769590858765
      },
      {
        "calls": 1,
        "instructions_per_call": 9058614.0,
        "state": {
          "gc_allocation_pressure": 61,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 3412737.0,
        "unexplained_share": 0.37673942172610514
      },
      {
        "calls": 1,
        "instructions_per_call": 8096103.0,
        "state": {
          "gc_allocation_pressure": 96,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 2497256.0,
        "unexplained_share": 0.3084516093730527
      },
      {
        "calls": 1,
        "instructions_per_call": 8081389.0,
        "state": {
          "gc_allocation_pressure": 133,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 2482824.0,
        "unexplained_share": 0.3072273838074123
      },
      {
        "calls": 1,
        "instructions_per_call": 9088365.0,
        "state": {
          "gc_allocation_pressure": 187,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 3441771.0,
        "unexplained_share": 0.37870078941591806
      },
      {
        "calls": 1,
        "instructions_per_call": 8124253.0,
        "state": {
          "gc_allocation_pressure": 229,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 2524807.0,
        "unexplained_share": 0.31077404901102906
      },
      {
        "calls": 2,
        "instructions_per_call": 8128500.5,
        "state": {
          "gc_allocation_pressure": 114,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2500021.0,
        "unexplained_share": 0.30756238496878974
      },
      {
        "calls": 2,
        "instructions_per_call": 8109716.5,
        "state": {
          "gc_allocation_pressure": 160,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2481431.0,
        "unexplained_share": 0.3059824594361591
      },
      {
        "calls": 2,
        "instructions_per_call": 8134828.0,
        "state": {
          "gc_allocation_pressure": 256,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 0,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2506535.5,
        "unexplained_share": 0.3081239701687608
      },
      {
        "calls": 1,
        "instructions_per_call": 8129954.0,
        "state": {
          "gc_allocation_pressure": 89,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2506759.0,
        "unexplained_share": 0.3083361849279836
      },
      {
        "calls": 1,
        "instructions_per_call": 8130495.0,
        "state": {
          "gc_allocation_pressure": 109,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2506674.0,
        "unexplained_share": 0.30830521388919124
      },
      {
        "calls": 1,
        "instructions_per_call": 8106642.0,
        "state": {
          "gc_allocation_pressure": 121,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2483644.0,
        "unexplained_share": 0.30637149142641307
      },
      {
        "calls": 1,
        "instructions_per_call": 8113400.0,
        "state": {
          "gc_allocation_pressure": 154,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2490334.0,
        "unexplained_share": 0.30694086326324355
      },
      {
        "calls": 1,
        "instructions_per_call": 8155953.0,
        "state": {
          "gc_allocation_pressure": 218,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2532406.0,
        "unexplained_share": 0.3104978657920172
      },
      {
        "calls": 1,
        "instructions_per_call": 8139910.0,
        "state": {
          "gc_allocation_pressure": 250,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 2516557.0,
        "unexplained_share": 0.3091627548707541
      },
      {
        "calls": 1,
        "instructions_per_call": 8174250.0,
        "state": {
          "gc_allocation_pressure": 107,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2513601.0,
        "unexplained_share": 0.3075023396641894
      },
      {
        "calls": 3,
        "instructions_per_call": 8176853.333333333,
        "state": {
          "gc_allocation_pressure": 121,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2516011.6666666665,
        "unexplained_share": 0.3076992535025698
      },
      {
        "calls": 1,
        "instructions_per_call": 8162781.0,
        "state": {
          "gc_allocation_pressure": 148,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2500656.0,
        "unexplained_share": 0.30634853489270386
      },
      {
        "calls": 3,
        "instructions_per_call": 8160162.333333333,
        "state": {
          "gc_allocation_pressure": 172,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2499146.999999999,
        "unexplained_share": 0.30626192199526087
      },
      {
        "calls": 1,
        "instructions_per_call": 8191920.0,
        "state": {
          "gc_allocation_pressure": 244,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2531543.0,
        "unexplained_share": 0.3090292629810838
      },
      {
        "calls": 3,
        "instructions_per_call": 8197664.0,
        "state": {
          "gc_allocation_pressure": 265,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2536664.6666666665,
        "unexplained_share": 0.3094375015451556
      },
      {
        "calls": 1,
        "instructions_per_call": 8185548.0,
        "state": {
          "gc_allocation_pressure": 102,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2529209.0,
        "unexplained_share": 0.3089846886243902
      },
      {
        "calls": 1,
        "instructions_per_call": 8178727.0,
        "state": {
          "gc_allocation_pressure": 116,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2523117.0,
        "unexplained_share": 0.3084975204576458
      },
      {
        "calls": 1,
        "instructions_per_call": 8167517.0,
        "state": {
          "gc_allocation_pressure": 143,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2511899.0,
        "unexplained_share": 0.3075474467944174
      },
      {
        "calls": 1,
        "instructions_per_call": 8169334.0,
        "state": {
          "gc_allocation_pressure": 166,
          "gc_older_generation_pressure": 2,
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2513971.0,
        "unexplained_share": 0.3077326744138506
      },
      {
        "calls": 1,
        "instructions_per_call": 8211104.0,
        "state": {
          "gc_allocation_pressure": 239,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2555147.0,
        "unexplained_share": 0.3111819068422468
      },
      {
        "calls": 1,
        "instructions_per_call": 8212921.0,
        "state": {
          "gc_allocation_pressure": 260,
          "gc_older_generation_pressure": 8,
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 2556908.0,
        "unexplained_share": 0.31132748019857975
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "39be52c5c8b8b33c748dd1ce77571405e796a315d8b13bdd0fa573c1ad6905ca",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 39.33769590858765,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 39.33769590858765,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "39be52c5c8b8b33c748dd1ce77571405e796a315d8b13bdd0fa573c1ad6905ca"
  }
}