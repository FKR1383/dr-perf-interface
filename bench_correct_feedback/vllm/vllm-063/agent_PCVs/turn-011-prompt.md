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

This is iteration 10. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Separating penalty preparation from other metadata work permits independent fitted scales for their different instruction paths. Rescaling alone did not help; this candidate changes the decomposition.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "int(self.batch_update_builder.batch_changed) * (3 + int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + int(not self.no_allowed_token_ids))",
        "name": "sampling_metadata_work",
        "rationale": "Groups metadata setup with sampling copies while separating penalty-specific work."
      },
      {
        "expression": "14 + self.num_reqs if self.batch_update_builder.batch_changed and (not self.no_penalties) else 0",
        "name": "penalty_metadata_work",
        "rationale": "Represents fixed penalty tensor preparation and the per-request prompt-padding loop."
      },
      {
        "expression": "int(len([ids for ids in self.req_output_token_ids if ids is not None and len(ids) <= 1]) > 0)",
        "name": "minimum_token_transition",
        "rationale": "Captures the fixed cost associated with initializing or expiring minimum-token masks."
      },
      {
        "expression": "len(self.batch_update_builder.added) + 2 * int(bool(self.batch_update_builder.added)) + 8 * int(bool(self.batch_update_builder.added) and self.all_greedy)",
        "name": "admission_work",
        "rationale": "Combines per-request initialization, admission setup, and the observed additional cost of all-greedy admission."
      }
    ]
  },
  "case_id": "vllm-063",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-063",
    "distinct_states": 21,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "admission_work": 872.2751641408933,
        "minimum_token_transition": 19183.790530964507,
        "penalty_metadata_work": 2594.2372185196286,
        "sampling_metadata_work": 10188.92277821349
      },
      "constant": 102061.20797539769,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 106.19567930791527,
    "max_unexplained_share": 0.41717929827792616,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "sampling_metadata_work",
      "penalty_metadata_work",
      "minimum_token_transition",
      "admission_work"
    ],
    "raw_files": [
      "run.2386683.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 11709.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 0
        },
        "unexplained_instructions_per_call": 3828.0,
        "unexplained_share": 0.3269280040994107
      },
      {
        "calls": 1,
        "instructions_per_call": 70825.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 0
        },
        "unexplained_instructions_per_call": 21677.0,
        "unexplained_share": 0.30606424285210027
      },
      {
        "calls": 2,
        "instructions_per_call": 84643.5,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 3
        },
        "unexplained_instructions_per_call": 22567.0,
        "unexplained_share": 0.2666123210878567
      },
      {
        "calls": 1,
        "instructions_per_call": 217180.0,
        "state": {
          "admission_work": 11,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 3
        },
        "unexplained_instructions_per_call": 90603.0,
        "unexplained_share": 0.41717929827792616
      },
      {
        "calls": 2,
        "instructions_per_call": 183341.5,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 15,
          "sampling_metadata_work": 3
        },
        "unexplained_instructions_per_call": 39159.5,
        "unexplained_share": 0.2135877583634911
      },
      {
        "calls": 2,
        "instructions_per_call": 194058.5,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 16,
          "sampling_metadata_work": 3
        },
        "unexplained_instructions_per_call": 40103.0,
        "unexplained_share": 0.20665417902333574
      },
      {
        "calls": 1,
        "instructions_per_call": 202941.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 17,
          "sampling_metadata_work": 3
        },
        "unexplained_instructions_per_call": 43066.0,
        "unexplained_share": 0.21220945989228396
      },
      {
        "calls": 1,
        "instructions_per_call": 156363.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 38380.0,
        "unexplained_share": 0.24545448731477396
      },
      {
        "calls": 1,
        "instructions_per_call": 215517.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 52739.0,
        "unexplained_share": 0.24470923407434217
      },
      {
        "calls": 1,
        "instructions_per_call": 247104.0,
        "state": {
          "admission_work": 4,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 0,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 74411.0,
        "unexplained_share": 0.3011323167573168
      },
      {
        "calls": 2,
        "instructions_per_call": 257352.5,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 16,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 50910.5,
        "unexplained_share": 0.1978239962697079
      },
      {
        "calls": 2,
        "instructions_per_call": 329640.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 17,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 72939.0,
        "unexplained_share": 0.2212686567164179
      },
      {
        "calls": 1,
        "instructions_per_call": 359065.0,
        "state": {
          "admission_work": 5,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 17,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 89461.0,
        "unexplained_share": 0.2491498753707546
      },
      {
        "calls": 2,
        "instructions_per_call": 270170.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 0,
          "penalty_metadata_work": 18,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 53989.5,
        "unexplained_share": 0.199835288892179
      },
      {
        "calls": 1,
        "instructions_per_call": 366694.0,
        "state": {
          "admission_work": 6,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 18,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 90642.0,
        "unexplained_share": 0.24718702787610378
      },
      {
        "calls": 2,
        "instructions_per_call": 342696.5,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 19,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 75584.0,
        "unexplained_share": 0.22055667332464732
      },
      {
        "calls": 1,
        "instructions_per_call": 375176.0,
        "state": {
          "admission_work": 7,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 19,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 90816.0,
        "unexplained_share": 0.2420623920506642
      },
      {
        "calls": 1,
        "instructions_per_call": 349258.0,
        "state": {
          "admission_work": 0,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 20,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 76750.0,
        "unexplained_share": 0.21975158765153555
      },
      {
        "calls": 1,
        "instructions_per_call": 388072.0,
        "state": {
          "admission_work": 8,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 20,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 94033.0,
        "unexplained_share": 0.24230812838854646
      },
      {
        "calls": 1,
        "instructions_per_call": 401475.0,
        "state": {
          "admission_work": 9,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 21,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 98966.0,
        "unexplained_share": 0.2465060090914752
      },
      {
        "calls": 1,
        "instructions_per_call": 415440.0,
        "state": {
          "admission_work": 10,
          "minimum_token_transition": 1,
          "penalty_metadata_work": 22,
          "sampling_metadata_work": 6
        },
        "unexplained_instructions_per_call": 102852.0,
        "unexplained_share": 0.2475736568457539
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 41.71792982779262,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 41.71792982779262,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6"
  }
}