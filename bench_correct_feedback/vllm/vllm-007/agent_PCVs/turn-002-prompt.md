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
    "hypothesis": "For this full-attention workload, the marked region performs no token-dependent block eviction; instruction count should be approximately constant plus per-group dispatch overhead.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(self.coordinator.single_type_managers)",
        "name": "cache_groups",
        "rationale": "The coordinator dispatches removal to each cache-group manager. OPT uses full attention, where skipped-block removal should require constant work per group."
      }
    ]
  },
  "case_id": "vllm-007",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 88,
    "case": "vllm-007",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 3"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 100.20197538286448,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "cache_groups"
    ],
    "raw_files": [
      "run.2222049.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 88,
        "instructions_per_call": 5552.090909090909,
        "state": {
          "cache_groups": 1
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5b69afe0adc6e40f0e35d5d2d8d9d3e4c65a9a6ca07d21dfdf7875941148c09a",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 1; need 3",
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
        "insufficient state points: 1; need 3",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "5b69afe0adc6e40f0e35d5d2d8d9d3e4c65a9a6ca07d21dfdf7875941148c09a"
  }
}