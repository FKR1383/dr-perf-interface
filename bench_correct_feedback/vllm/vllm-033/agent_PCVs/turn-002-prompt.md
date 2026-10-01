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
    "hypothesis": "Running requests in this workload predominantly schedule one decode token. Their instruction counts should have a stable base cost, with variation explained by existing block count and allocation or caching at block boundaries.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "request.num_computed_tokens // self.block_size",
        "name": "existing_full_blocks",
        "rationale": "Tracks sequence-dependent block bookkeeping during slot allocation and prefix caching."
      },
      {
        "expression": "int(request.num_computed_tokens % self.block_size == 0)",
        "name": "needs_new_block",
        "rationale": "For the workload's single-token decode steps, a block-aligned entry requires allocating another KV block."
      },
      {
        "expression": "int((request.num_computed_tokens + 1) % self.block_size == 0)",
        "name": "completes_full_block",
        "rationale": "Identifies decode steps that complete a block and can trigger prefix-cache registration."
      }
    ]
  },
  "case_id": "vllm-033",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 52,
    "case": "vllm-033",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 5"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 94.31154508283362,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "existing_full_blocks",
      "needs_new_block",
      "completes_full_block"
    ],
    "raw_files": [
      "run.2267477.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 52,
        "instructions_per_call": 63439.019230769234,
        "state": {
          "completes_full_block": 0,
          "existing_full_blocks": 0,
          "needs_new_block": 0
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "30f279e661826197509547e6b241d571ed7d0d8eafddb4538fa819f91749ecfe",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 1; need 5",
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
        "insufficient state points: 1; need 5",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "30f279e661826197509547e6b241d571ed7d0d8eafddb4538fa819f91749ecfe"
  }
}