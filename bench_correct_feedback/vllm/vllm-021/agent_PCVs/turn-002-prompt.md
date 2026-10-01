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
    "hypothesis": "Instruction count is approximately constant across the supplied nonempty queues; heap cardinality and front priority do not affect the work of peeking.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "int(bool(self._heap))",
        "name": "heap_nonempty",
        "rationale": "Captures the branch between raising on an empty heap and returning its first element. The tested nonempty path performs constant work regardless of queue size or request attributes."
      }
    ]
  },
  "case_id": "vllm-021",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 24,
    "case": "vllm-021",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 3"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 11.773221152834594,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "heap_nonempty"
    ],
    "raw_files": [
      "run.2245867.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 24,
        "instructions_per_call": 2137.0833333333335,
        "state": {
          "heap_nonempty": 1
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "7502f6d7b3f9c490cd1b18f07b5a241d1a496ac1b454d342aeaec03e52ed5c3d",
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
    "workload_digest": "7502f6d7b3f9c490cd1b18f07b5a241d1a496ac1b454d342aeaec03e52ed5c3d"
  }
}