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

This is iteration 5. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "A compressed metadata-work predictor permits separate modeling of minimum-token transitions, admission work, and the unusually expensive all-greedy admission regime.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "int(self.batch_update_builder.batch_changed) * (12 + 4 * (int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties) + int(not self.no_allowed_token_ids)) + (4 + self.num_reqs if not self.no_penalties else 0))",
        "name": "metadata_work_units",
        "rationale": "Combines metadata setup, tensor copies, and penalty prompt construction into approximate work units, freeing features for processor transitions."
      },
      {
        "expression": "int(len([ids for ids in self.req_output_token_ids if ids is not None and len(ids) <= 1]) > 0)",
        "name": "minimum_token_transition",
        "rationale": "Separates minimum-token mask transitions, which the previous report associates with roughly 60000 additional instructions."
      },
      {
        "expression": "len(self.batch_update_builder.added) + int(bool(self.batch_update_builder.added))",
        "name": "addition_work",
        "rationale": "Represents both fixed admission setup and per-request processor initialization."
      },
      {
        "expression": "int(bool(self.batch_update_builder.added) and self.all_greedy)",
        "name": "greedy_admission",
        "rationale": "Separates admission into an all-greedy batch, which showed substantially greater residual cost than other admissions."
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
        "addition_work": 3660.0695960738344,
        "greedy_admission": 20106.08826002505,
        "metadata_work_units": 3261.308719940488,
        "minimum_token_transition": 20689.064238700288
      },
      "constant": 78257.54255095295,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 102.70614902395755,
    "max_unexplained_share": 0.3218449907583696,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "metadata_work_units",
      "minimum_token_transition",
      "addition_work",
      "greedy_admission"
    ],
    "raw_files": [
      "run.2382213.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 11444.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 0,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 3073.0,
        "unexplained_share": 0.2685249912617966
      },
      {
        "calls": 1,
        "instructions_per_call": 70780.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 0,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 17353.0,
        "unexplained_share": 0.24516812658943204
      },
      {
        "calls": 2,
        "instructions_per_call": 84514.5,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 12,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 20894.5,
        "unexplained_share": 0.24722976530654503
      },
      {
        "calls": 1,
        "instructions_per_call": 215871.0,
        "state": {
          "addition_work": 2,
          "greedy_admission": 1,
          "metadata_work_units": 12,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 69477.0,
        "unexplained_share": 0.3218449907583696
      },
      {
        "calls": 1,
        "instructions_per_call": 156175.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 24,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 34652.0,
        "unexplained_share": 0.2218793020649912
      },
      {
        "calls": 1,
        "instructions_per_call": 216011.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 24,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 46757.0,
        "unexplained_share": 0.21645656934137614
      },
      {
        "calls": 1,
        "instructions_per_call": 247500.0,
        "state": {
          "addition_work": 3,
          "greedy_admission": 0,
          "metadata_work_units": 24,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 62803.0,
        "unexplained_share": 0.25374949494949495
      },
      {
        "calls": 2,
        "instructions_per_call": 184073.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 29,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 37388.5,
        "unexplained_share": 0.2031177847919032
      },
      {
        "calls": 2,
        "instructions_per_call": 194195.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 30,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 38158.5,
        "unexplained_share": 0.19649579031385978
      },
      {
        "calls": 1,
        "instructions_per_call": 203454.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 31,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 41647.0,
        "unexplained_share": 0.20469983386908097
      },
      {
        "calls": 2,
        "instructions_per_call": 257674.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 42,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 47684.5,
        "unexplained_share": 0.18505747572514106
      },
      {
        "calls": 2,
        "instructions_per_call": 330556.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 43,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 66152.5,
        "unexplained_share": 0.2001249410084827
      },
      {
        "calls": 1,
        "instructions_per_call": 358799.0,
        "state": {
          "addition_work": 4,
          "greedy_admission": 0,
          "metadata_work_units": 43,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 74488.0,
        "unexplained_share": 0.20760370012179521
      },
      {
        "calls": 2,
        "instructions_per_call": 270125.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 44,
          "minimum_token_transition": 0
        },
        "unexplained_instructions_per_call": 51100.0,
        "unexplained_share": 0.1891716797778806
      },
      {
        "calls": 1,
        "instructions_per_call": 365847.0,
        "state": {
          "addition_work": 5,
          "greedy_admission": 0,
          "metadata_work_units": 44,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 74433.0,
        "unexplained_share": 0.20345390286103207
      },
      {
        "calls": 2,
        "instructions_per_call": 343228.5,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 45,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 69107.5,
        "unexplained_share": 0.20134545936599088
      },
      {
        "calls": 1,
        "instructions_per_call": 374637.0,
        "state": {
          "addition_work": 6,
          "greedy_admission": 0,
          "metadata_work_units": 45,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 73420.0,
        "unexplained_share": 0.19597637179456381
      },
      {
        "calls": 1,
        "instructions_per_call": 349893.0,
        "state": {
          "addition_work": 0,
          "greedy_admission": 0,
          "metadata_work_units": 46,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 70304.0,
        "unexplained_share": 0.20092999859957186
      },
      {
        "calls": 1,
        "instructions_per_call": 388929.0,
        "state": {
          "addition_work": 7,
          "greedy_admission": 0,
          "metadata_work_units": 46,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 75605.0,
        "unexplained_share": 0.19439280691334407
      },
      {
        "calls": 1,
        "instructions_per_call": 401615.0,
        "state": {
          "addition_work": 8,
          "greedy_admission": 0,
          "metadata_work_units": 47,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 78408.0,
        "unexplained_share": 0.19523175180209904
      },
      {
        "calls": 1,
        "instructions_per_call": 415737.0,
        "state": {
          "addition_work": 9,
          "greedy_admission": 0,
          "metadata_work_units": 48,
          "minimum_token_transition": 1
        },
        "unexplained_instructions_per_call": 80208.0,
        "unexplained_share": 0.1929296646678068
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 32.18449907583696,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 32.18449907583696,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "15cb069e1e164957204fba6aa8507df88818eecdc1a5ee90ac4f12b853520ba6"
  }
}