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
    "hypothesis": "Instruction count is approximately a fixed entry cost plus active-path overhead, per-block work, and per-token hashing preparation.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "max(0, request.num_tokens // hash_block_size - len(request.block_hashes))",
        "name": "new_full_blocks",
        "rationale": "Counts loop iterations, each generating extra keys, slicing tokens, and computing one chained hash."
      },
      {
        "expression": "int(request.num_tokens // hash_block_size > len(request.block_hashes))",
        "name": "hashing_active",
        "rationale": "Captures setup and termination costs skipped by the early return."
      },
      {
        "expression": "max(0, request.num_tokens // hash_block_size - len(request.block_hashes)) * hash_block_size",
        "name": "new_full_block_tokens",
        "rationale": "Captures token slicing, tuple construction, and serialization work proportional to the number of tokens hashed."
      }
    ]
  },
  "case_id": "vllm-013",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 124,
    "case": "vllm-013",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 5"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 96.26557770278305,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "new_full_blocks",
      "hashing_active",
      "new_full_block_tokens"
    ],
    "raw_files": [
      "run.2239946.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 124,
        "instructions_per_call": 3001.7903225806454,
        "state": {
          "hashing_active": 0,
          "new_full_block_tokens": 0,
          "new_full_blocks": 0
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5f00eac657525e2c6fff57ddd974b54402cd14e9e3895ee1e5ee46511f913e3b",
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
    "workload_digest": "5f00eac657525e2c6fff57ddd974b54402cd14e9e3895ee1e5ee46511f913e3b"
  }
}