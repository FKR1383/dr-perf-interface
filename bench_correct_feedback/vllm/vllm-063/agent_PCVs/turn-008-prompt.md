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

This is iteration 7. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Explicitly separating steady refreshes, minimum-token transitions, and admission regimes may explain instruction paths that a single combined predictor merged.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "2 + int(self.batch_update_builder.batch_changed) * (12 + 4 * (int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties)) + (4 + self.num_reqs if not self.no_penalties else 0)) if not self.batch_update_builder.added and len([ids for ids in self.req_output_token_ids if ids is not None and len(ids) <= 1]) == 0 else 0",
        "name": "steady_refresh_work",
        "rationale": "Models baseline and metadata work when neither admissions nor minimum-token transitions occur."
      },
      {
        "expression": "12 + int(self.batch_update_builder.batch_changed) * (12 + 4 * (int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties)) + (4 + self.num_reqs if not self.no_penalties else 0)) if not self.batch_update_builder.added and len([ids for ids in self.req_output_token_ids if ids is not None and len(ids) <= 1]) > 0 else 0",
        "name": "transition_refresh_work",
        "rationale": "Separates refreshes that update minimum-token masks for existing requests."
      },
      {
        "expression": "25 + len(self.batch_update_builder.added) + 4 * (int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties)) + (4 + self.num_reqs if not self.no_penalties else 0) if self.batch_update_builder.added and (not self.all_greedy) else 0",
        "name": "sampled_admission_work",
        "rationale": "Models admission setup, request initialization, and metadata construction for batches containing sampled requests."
      },
      {
        "expression": "int(bool(self.batch_update_builder.added) and self.all_greedy)",
        "name": "greedy_admission",
        "rationale": "Retains a separate predictor for the observed expensive all-greedy admission path."
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
        "greedy_admission": 67348.09426798555,
        "sampled_admission_work": 3109.281647719939,
        "steady_refresh_work": 2973.7701235101867,
        "transition_refresh_work": 2996.3147657486884
      },
      "constant": 60347.45531680668,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 131.41133579518646,
    "max_unexplained_share": 0.366344532069107,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "steady_refresh_work",
      "transition_refresh_work",
      "sampled_admission_work",
      "greedy_admission"
    ],
    "raw_files": [
      "run.2383931.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 219370.0,
        "state": {
          "greedy_admission": 1,
          "sampled_admission_work": 0,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 80365.0,
        "unexplained_share": 0.366344532069107
      },
      {
        "calls": 1,
        "instructions_per_call": 247502.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 39,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 77462.0,
        "unexplained_share": 0.3129752486848591
      },
      {
        "calls": 1,
        "instructions_per_call": 358089.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 59,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 96579.0,
        "unexplained_share": 0.26970669302882805
      },
      {
        "calls": 1,
        "instructions_per_call": 366138.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 61,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 98401.0,
        "unexplained_share": 0.268753857835024
      },
      {
        "calls": 1,
        "instructions_per_call": 374630.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 63,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 98215.0,
        "unexplained_share": 0.2621653364653124
      },
      {
        "calls": 1,
        "instructions_per_call": 387762.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 65,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 101231.0,
        "unexplained_share": 0.261064776847654
      },
      {
        "calls": 1,
        "instructions_per_call": 401793.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 67,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 105875.0,
        "unexplained_share": 0.26350633286294184
      },
      {
        "calls": 1,
        "instructions_per_call": 418102.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 69,
          "steady_refresh_work": 0,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 110123.0,
        "unexplained_share": 0.2633878814260635
      },
      {
        "calls": 1,
        "instructions_per_call": 70612.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 0,
          "transition_refresh_work": 12
        },
        "unexplained_instructions_per_call": 21865.0,
        "unexplained_share": 0.3096499178609868
      },
      {
        "calls": 1,
        "instructions_per_call": 217133.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 0,
          "transition_refresh_work": 36
        },
        "unexplained_instructions_per_call": 60301.0,
        "unexplained_share": 0.2777145804645079
      },
      {
        "calls": 2,
        "instructions_per_call": 329691.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 0,
          "transition_refresh_work": 55
        },
        "unexplained_instructions_per_call": 85321.5,
        "unexplained_share": 0.2587923237213027
      },
      {
        "calls": 2,
        "instructions_per_call": 343133.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 0,
          "transition_refresh_work": 57
        },
        "unexplained_instructions_per_call": 89164.0,
        "unexplained_share": 0.2598525936007321
      },
      {
        "calls": 1,
        "instructions_per_call": 349133.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 0,
          "transition_refresh_work": 58
        },
        "unexplained_instructions_per_call": 90102.0,
        "unexplained_share": 0.258073570816852
      },
      {
        "calls": 1,
        "instructions_per_call": 11709.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 2,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 3401.0,
        "unexplained_share": 0.2904603296609446
      },
      {
        "calls": 2,
        "instructions_per_call": 84388.5,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 14,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 24768.0,
        "unexplained_share": 0.2934997067135925
      },
      {
        "calls": 1,
        "instructions_per_call": 156052.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 26,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 42818.0,
        "unexplained_share": 0.2743828980083562
      },
      {
        "calls": 2,
        "instructions_per_call": 183351.5,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 31,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 46739.0,
        "unexplained_share": 0.2549147402666463
      },
      {
        "calls": 2,
        "instructions_per_call": 193883.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 32,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 48486.0,
        "unexplained_share": 0.25007865568409815
      },
      {
        "calls": 1,
        "instructions_per_call": 201944.0,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 33,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 51480.0,
        "unexplained_share": 0.25492215663748363
      },
      {
        "calls": 2,
        "instructions_per_call": 258336.5,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 44,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 62814.0,
        "unexplained_share": 0.2431479872182212
      },
      {
        "calls": 2,
        "instructions_per_call": 269972.5,
        "state": {
          "greedy_admission": 0,
          "sampled_admission_work": 0,
          "steady_refresh_work": 46,
          "transition_refresh_work": 0
        },
        "unexplained_instructions_per_call": 66127.5,
        "unexplained_share": 0.2449416144236913
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 36.6344532069107,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 36.6344532069107,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6"
  }
}