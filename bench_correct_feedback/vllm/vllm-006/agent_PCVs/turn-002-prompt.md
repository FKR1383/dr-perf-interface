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
    "hypothesis": "For the single-group OPT workload, instruction count should be explained primarily by fixed initial-admission overhead plus the numbers of newly allocated, newly cached, and reused prefix blocks.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "max(0, (min(request.num_computed_tokens + num_new_computed_tokens + num_external_computed_tokens + num_new_tokens + num_lookahead_tokens, self.max_model_len) + self.coordinator.single_type_managers[0].block_size - 1) // self.coordinator.single_type_managers[0].block_size - max(len(self.coordinator.single_type_managers[0].req_to_blocks.get(request.request_id, ())), len(new_computed_blocks.blocks[0]) if new_computed_blocks is not None else 0))",
        "name": "new_blocks",
        "rationale": "Estimates newly allocated blocks, which drive block-pool allocation and request-table updates."
      },
      {
        "expression": "max(0, min(min(request.num_computed_tokens + num_new_computed_tokens + num_external_computed_tokens, self.max_model_len) + num_new_tokens, request.num_tokens) // self.coordinator.single_type_managers[0].block_size - (request.num_computed_tokens + num_new_computed_tokens) // self.coordinator.single_type_managers[0].block_size) if self.enable_caching and (not delay_cache_blocks) else 0",
        "name": "new_full_cached_blocks",
        "rationale": "Estimates newly completed blocks requiring hash assignment and prefix-cache insertion."
      },
      {
        "expression": "len(new_computed_blocks.blocks[0]) if new_computed_blocks is not None else 0",
        "name": "prefix_hit_blocks",
        "rationale": "Captures work attaching and touching reused prefix blocks."
      },
      {
        "expression": "int(request.num_computed_tokens == 0)",
        "name": "initial_allocation",
        "rationale": "Separates initial request admission and bookkeeping from incremental decoding."
      }
    ]
  },
  "case_id": "vllm-006",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 88,
    "case": "vllm-006",
    "distinct_states": 2,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 2; need 6"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 123.44930144678801,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "new_blocks",
      "new_full_cached_blocks",
      "prefix_hit_blocks",
      "initial_allocation"
    ],
    "raw_files": [
      "run.1803058.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 52,
        "instructions_per_call": 45162.96153846154,
        "state": {
          "initial_allocation": 0,
          "new_blocks": 0,
          "new_full_cached_blocks": 0,
          "prefix_hit_blocks": 0
        }
      },
      {
        "calls": 36,
        "instructions_per_call": 76597.02777777778,
        "state": {
          "initial_allocation": 1,
          "new_blocks": 1,
          "new_full_cached_blocks": 0,
          "prefix_hit_blocks": 0
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "cd8431f9c844bce8867d4cb27e203f229e5dadc4fb6f98790440f14218aa0995",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 2; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "success": false,
      "threshold_percent": 10.0,
      "valid": false
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": null,
      "iteration": 1,
      "reasons": [
        "insufficient state points: 2; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "cd8431f9c844bce8867d4cb27e203f229e5dadc4fb6f98790440f14218aa0995"
  }
}