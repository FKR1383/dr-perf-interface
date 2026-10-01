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
    "hypothesis": "Conditional tensor copies and penalty-triggered prompt construction dominate instruction count, with prompt construction scaling with row count and tensor size.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "int(not self.all_greedy) + int(not self.no_top_p) + int(not self.no_top_k) + 3 * int(not self.no_penalties)",
        "name": "sampling_copy_count",
        "rationale": "Counts conditional sampling tensor copies and their fixed library overhead."
      },
      {
        "expression": "int(not self.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures the fixed prompt tensor construction overhead triggered by penalties in this workload."
      },
      {
        "expression": "self.num_reqs if not self.no_penalties else 0",
        "name": "prompt_rows",
        "rationale": "Tracks iterations of the prompt padding loop."
      },
      {
        "expression": "self.num_reqs * int(max(self.num_prompt_tokens[:self.num_reqs])) if self.num_reqs and (not self.no_penalties) else 0",
        "name": "prompt_elements",
        "rationale": "Tracks the rectangular prompt tensor size using a bounded entry-state reduction."
      }
    ]
  },
  "case_id": "vllm-060",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 27,
    "case": "vllm-060",
    "distinct_states": 21,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "penalties_enabled": 20259.636990812294,
        "prompt_elements": -14.934955997144087,
        "prompt_rows": 5616.30314387266,
        "sampling_copy_count": 20104.101099205815
      },
      "constant": 65261.78005486329,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 127.50255359243602,
    "max_unexplained_share": 0.1389048716630521,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "sampling_copy_count",
      "penalties_enabled",
      "prompt_rows",
      "prompt_elements"
    ],
    "raw_files": [
      "run.2371111.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 73429.75,
        "state": {
          "penalties_enabled": 0,
          "prompt_elements": 0,
          "prompt_rows": 0,
          "sampling_copy_count": 0
        },
        "unexplained_instructions_per_call": 10199.75,
        "unexplained_share": 0.1389048716630521
      },
      {
        "calls": 3,
        "instructions_per_call": 125121.66666666667,
        "state": {
          "penalties_enabled": 0,
          "prompt_elements": 0,
          "prompt_rows": 0,
          "sampling_copy_count": 3
        },
        "unexplained_instructions_per_call": 6974.666666666668,
        "unexplained_share": 0.05574307673864106
      },
      {
        "calls": 1,
        "instructions_per_call": 156760.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 45,
          "prompt_rows": 1,
          "sampling_copy_count": 3
        },
        "unexplained_instructions_per_call": 8518.0,
        "unexplained_share": 0.054337841286042354
      },
      {
        "calls": 1,
        "instructions_per_call": 155901.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 46,
          "prompt_rows": 1,
          "sampling_copy_count": 3
        },
        "unexplained_instructions_per_call": 7889.0,
        "unexplained_share": 0.05060262602549054
      },
      {
        "calls": 1,
        "instructions_per_call": 160499.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 42,
          "prompt_rows": 2,
          "sampling_copy_count": 3
        },
        "unexplained_instructions_per_call": 7969.0,
        "unexplained_share": 0.04965139969719438
      },
      {
        "calls": 1,
        "instructions_per_call": 161023.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 92,
          "prompt_rows": 2,
          "sampling_copy_count": 3
        },
        "unexplained_instructions_per_call": 8283.0,
        "unexplained_share": 0.05143985641802724
      },
      {
        "calls": 1,
        "instructions_per_call": 169101.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 135,
          "prompt_rows": 3,
          "sampling_copy_count": 3
        },
        "unexplained_instructions_per_call": 10429.0,
        "unexplained_share": 0.06167320122293777
      },
      {
        "calls": 1,
        "instructions_per_call": 226553.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 90,
          "prompt_rows": 2,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 9758.0,
        "unexplained_share": 0.04307159914015705
      },
      {
        "calls": 1,
        "instructions_per_call": 226154.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 92,
          "prompt_rows": 2,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 9645.0,
        "unexplained_share": 0.04264793017147608
      },
      {
        "calls": 1,
        "instructions_per_call": 231073.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 63,
          "prompt_rows": 3,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 9922.0,
        "unexplained_share": 0.04293881154440372
      },
      {
        "calls": 1,
        "instructions_per_call": 242194.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 66,
          "prompt_rows": 3,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 16226.0,
        "unexplained_share": 0.06699587933639975
      },
      {
        "calls": 1,
        "instructions_per_call": 236754.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 138,
          "prompt_rows": 3,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 14139.0,
        "unexplained_share": 0.05972021592032236
      },
      {
        "calls": 1,
        "instructions_per_call": 247414.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 84,
          "prompt_rows": 4,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 14646.0,
        "unexplained_share": 0.05919632680446539
      },
      {
        "calls": 1,
        "instructions_per_call": 239197.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 184,
          "prompt_rows": 4,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 12064.0,
        "unexplained_share": 0.05043541515988913
      },
      {
        "calls": 1,
        "instructions_per_call": 239010.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 188,
          "prompt_rows": 4,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 11974.0,
        "unexplained_share": 0.05009832224593113
      },
      {
        "calls": 1,
        "instructions_per_call": 245686.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 225,
          "prompt_rows": 5,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 13933.0,
        "unexplained_share": 0.0567105980804767
      },
      {
        "calls": 2,
        "instructions_per_call": 246040.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 230,
          "prompt_rows": 5,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 12648.5,
        "unexplained_share": 0.05140830759226142
      },
      {
        "calls": 1,
        "instructions_per_call": 248879.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 270,
          "prompt_rows": 6,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 10514.0,
        "unexplained_share": 0.04224542850140028
      },
      {
        "calls": 1,
        "instructions_per_call": 250966.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 282,
          "prompt_rows": 6,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 14088.0,
        "unexplained_share": 0.05613509399679638
      },
      {
        "calls": 1,
        "instructions_per_call": 252989.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 322,
          "prompt_rows": 7,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 10262.0,
        "unexplained_share": 0.04056302843206622
      },
      {
        "calls": 1,
        "instructions_per_call": 256257.0,
        "state": {
          "penalties_enabled": 1,
          "prompt_elements": 376,
          "prompt_rows": 8,
          "sampling_copy_count": 6
        },
        "unexplained_instructions_per_call": 10470.0,
        "unexplained_share": 0.04085742048022103
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "2df2d18b6ac71d6f2ee680067f6e7b6f5a7b3f697e7551ca5a1a9c067886b8ff",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 13.89048716630521,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 13.89048716630521,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "2df2d18b6ac71d6f2ee680067f6e7b6f5a7b3f697e7551ca5a1a9c067886b8ff"
  }
}