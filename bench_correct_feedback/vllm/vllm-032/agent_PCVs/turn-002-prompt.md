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
    "hypothesis": "Instruction count is primarily an affine combination of running and waiting request counts, with additional work proportional to waiting prompt blocks and new blocks required by running requests.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(self.running)",
        "name": "running_requests",
        "rationale": "Captures per-request scheduling, allocation checks, cached output construction, and state updates."
      },
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting)",
        "name": "waiting_requests",
        "rationale": "Captures admission, prefix lookup, queue operations, and new-request output construction."
      },
      {
        "expression": "sum(((r.num_tokens + self.block_size - 1) // self.block_size for r in self.waiting))",
        "name": "waiting_prompt_blocks",
        "rationale": "Approximates block-dependent prefix lookup, allocation, and block-ID materialization during admission."
      },
      {
        "expression": "sum(((r.num_tokens_with_spec + self.block_size - 1) // self.block_size - (r.num_computed_tokens + self.block_size - 1) // self.block_size for r in self.running))",
        "name": "running_block_boundaries",
        "rationale": "Captures additional KV-block allocation when running requests cross block boundaries."
      }
    ]
  },
  "case_id": "vllm-032",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-032",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "running_block_boundaries": 0.0,
        "running_requests": 39481.55951666611,
        "waiting_prompt_blocks": 0.0,
        "waiting_requests": 88253.37250942379
      },
      "constant": 51841.43515655052,
      "dependent_columns": [
        2,
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 119.88901376584545,
    "max_unexplained_share": 0.6352974086934652,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests",
      "waiting_requests",
      "waiting_prompt_blocks",
      "running_block_boundaries"
    ],
    "raw_files": [
      "run.2257877.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 389649.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 1,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 247543.0,
        "unexplained_share": 0.6352974086934652
      },
      {
        "calls": 1,
        "instructions_per_call": 482961.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 2,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 256261.0,
        "unexplained_share": 0.5306039203993698
      },
      {
        "calls": 1,
        "instructions_per_call": 524469.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 3,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 212889.0,
        "unexplained_share": 0.40591340956281496
      },
      {
        "calls": 1,
        "instructions_per_call": 661568.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 4,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 261358.0,
        "unexplained_share": 0.3950584066943988
      },
      {
        "calls": 1,
        "instructions_per_call": 816642.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 5,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 324548.0,
        "unexplained_share": 0.3974177179229087
      },
      {
        "calls": 1,
        "instructions_per_call": 962994.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 6,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 380664.0,
        "unexplained_share": 0.39529218250581
      },
      {
        "calls": 1,
        "instructions_per_call": 1114755.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 7,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 441843.0,
        "unexplained_share": 0.39635884118034903
      },
      {
        "calls": 1,
        "instructions_per_call": 1258520.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 0,
          "waiting_prompt_blocks": 8,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 495445.0,
        "unexplained_share": 0.39367272669484793
      },
      {
        "calls": 5,
        "instructions_per_call": 146707.8,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 1,
          "waiting_prompt_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 60386.000000000015,
        "unexplained_share": 0.41160729013726616
      },
      {
        "calls": 7,
        "instructions_per_call": 222263.85714285713,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 2,
          "waiting_prompt_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 94460.57142857136,
        "unexplained_share": 0.4249929459644808
      },
      {
        "calls": 3,
        "instructions_per_call": 287683.6666666667,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 3,
          "waiting_prompt_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 118787.99999999999,
        "unexplained_share": 0.41291186731722684
      },
      {
        "calls": 2,
        "instructions_per_call": 360368.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 4,
          "waiting_prompt_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 150050.5,
        "unexplained_share": 0.41638131021622343
      },
      {
        "calls": 2,
        "instructions_per_call": 431460.5,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 5,
          "waiting_prompt_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 178346.5,
        "unexplained_share": 0.4133553361199924
      },
      {
        "calls": 1,
        "instructions_per_call": 501383.0,
        "state": {
          "running_block_boundaries": 0,
          "running_requests": 6,
          "waiting_prompt_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 206828.0,
        "unexplained_share": 0.41251498355548555
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 63.52974086934652,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 63.52974086934652,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}