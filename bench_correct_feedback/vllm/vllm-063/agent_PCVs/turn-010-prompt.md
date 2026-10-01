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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The best previous feature set closely tracks observed costs, but fitted coefficients substantially understate their apparent slopes. Rescaling that same basis tests whether numerical scaling contributes to the unexplained share.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "1024 * int(self.batch_update_builder.batch_changed) * (12 + 4 * (int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties) + int(not self.no_allowed_token_ids)) + (4 + self.num_reqs if not self.no_penalties else 0))",
        "name": "metadata_work_scaled",
        "rationale": "Preserves the strongest previous metadata predictor while testing sensitivity to feature scale."
      },
      {
        "expression": "1024 * int(len([ids for ids in self.req_output_token_ids if ids is not None and len(ids) <= 1]) > 0)",
        "name": "minimum_token_transition_scaled",
        "rationale": "Captures fixed minimum-token transition work using the same scale."
      },
      {
        "expression": "1024 * (len(self.batch_update_builder.added) + int(bool(self.batch_update_builder.added)))",
        "name": "addition_work_scaled",
        "rationale": "Captures fixed admission setup and per-request initialization."
      },
      {
        "expression": "1024 * int(bool(self.batch_update_builder.added) and self.all_greedy)",
        "name": "greedy_admission_scaled",
        "rationale": "Separates the unusually expensive all-greedy admission path."
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
        "addition_work_scaled": 3.5728723114587484,
        "greedy_admission_scaled": 18.876053977949063,
        "metadata_work_scaled": 3.1819112320448144,
        "minimum_token_transition_scaled": 20.202151420353996
      },
      "constant": 78177.61400751864,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 129.1237631989643,
    "max_unexplained_share": 0.3291733245174206,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "metadata_work_scaled",
      "minimum_token_transition_scaled",
      "addition_work_scaled",
      "greedy_admission_scaled"
    ],
    "raw_files": [
      "run.2385769.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 11671.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 0,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 3197.0,
        "unexplained_share": 0.27392682717847655
      },
      {
        "calls": 1,
        "instructions_per_call": 70845.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 0,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 17437.0,
        "unexplained_share": 0.24612887289152374
      },
      {
        "calls": 2,
        "instructions_per_call": 84833.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 12288,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 21070.5,
        "unexplained_share": 0.2483762215175698
      },
      {
        "calls": 1,
        "instructions_per_call": 217788.0,
        "state": {
          "addition_work_scaled": 2048,
          "greedy_admission_scaled": 1024,
          "metadata_work_scaled": 12288,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 71690.0,
        "unexplained_share": 0.3291733245174206
      },
      {
        "calls": 1,
        "instructions_per_call": 156566.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 24576,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 34903.0,
        "unexplained_share": 0.22292834970555547
      },
      {
        "calls": 1,
        "instructions_per_call": 215656.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 24576,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 46549.0,
        "unexplained_share": 0.2158483881737582
      },
      {
        "calls": 1,
        "instructions_per_call": 246518.0,
        "state": {
          "addition_work_scaled": 3072,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 24576,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 62122.0,
        "unexplained_share": 0.2519978257165805
      },
      {
        "calls": 2,
        "instructions_per_call": 183358.5,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 29696,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 37076.0,
        "unexplained_share": 0.20220497004502108
      },
      {
        "calls": 2,
        "instructions_per_call": 195163.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 30720,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 38722.0,
        "unexplained_share": 0.19840850980974878
      },
      {
        "calls": 1,
        "instructions_per_call": 202468.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 31744,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 41181.0,
        "unexplained_share": 0.20339510441156133
      },
      {
        "calls": 2,
        "instructions_per_call": 257097.5,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 43008,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 47366.5,
        "unexplained_share": 0.1842355526599831
      },
      {
        "calls": 2,
        "instructions_per_call": 329068.5,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 44032,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 65490.0,
        "unexplained_share": 0.19901631423244703
      },
      {
        "calls": 1,
        "instructions_per_call": 359157.0,
        "state": {
          "addition_work_scaled": 4096,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 44032,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 74910.0,
        "unexplained_share": 0.2085717388217409
      },
      {
        "calls": 2,
        "instructions_per_call": 270975.5,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 45056,
          "minimum_token_transition_scaled": 0
        },
        "unexplained_instructions_per_call": 51593.0,
        "unexplained_share": 0.19039728683958512
      },
      {
        "calls": 1,
        "instructions_per_call": 365656.0,
        "state": {
          "addition_work_scaled": 5120,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 45056,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 74517.0,
        "unexplained_share": 0.20378990089045443
      },
      {
        "calls": 2,
        "instructions_per_call": 342456.5,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 46080,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 68706.0,
        "unexplained_share": 0.2006269409399442
      },
      {
        "calls": 1,
        "instructions_per_call": 374092.0,
        "state": {
          "addition_work_scaled": 6144,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 46080,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 73192.0,
        "unexplained_share": 0.19565240635993286
      },
      {
        "calls": 1,
        "instructions_per_call": 349017.0,
        "state": {
          "addition_work_scaled": 0,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 47104,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 69955.0,
        "unexplained_share": 0.20043436279608157
      },
      {
        "calls": 1,
        "instructions_per_call": 387143.0,
        "state": {
          "addition_work_scaled": 7168,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 47104,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 74725.0,
        "unexplained_share": 0.1930165339422384
      },
      {
        "calls": 1,
        "instructions_per_call": 402318.0,
        "state": {
          "addition_work_scaled": 8192,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 48128,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 78836.0,
        "unexplained_share": 0.19595444399703718
      },
      {
        "calls": 1,
        "instructions_per_call": 414688.0,
        "state": {
          "addition_work_scaled": 9216,
          "greedy_admission_scaled": 0,
          "metadata_work_scaled": 49152,
          "minimum_token_transition_scaled": 1024
        },
        "unexplained_instructions_per_call": 79958.0,
        "unexplained_share": 0.19281483910795585
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 32.91733245174206,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 32.91733245174206,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6"
  }
}