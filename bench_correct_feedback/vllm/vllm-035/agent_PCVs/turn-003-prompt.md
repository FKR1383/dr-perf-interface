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
    "hypothesis": "Instruction count should primarily follow admitted request count, KV block demand, and priority-queue removal work. Empty waiting queues should incur nearly constant cost.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting)",
        "name": "waiting_requests",
        "rationale": "Captures per-request queue traversal, admission checks, and scheduling bookkeeping."
      },
      {
        "expression": "sum(((r.num_tokens + self.block_size - 1) // self.block_size for r in self.waiting))",
        "name": "waiting_blocks",
        "rationale": "Estimates block allocation and prefix-cache processing work across waiting requests."
      },
      {
        "expression": "len(self.waiting) * (0 if len(self.waiting) == 0 else 1 if len(self.waiting) < 2 else 2 if len(self.waiting) < 4 else 3 if len(self.waiting) < 8 else 4)",
        "name": "priority_queue_work",
        "rationale": "Approximates heap removal work for the workload's queues of at most eight requests using cheap comparisons."
      }
    ]
  },
  "case_id": "vllm-035",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-035",
    "distinct_states": 9,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "priority_queue_work": 88.89440188568085,
        "waiting_blocks": 0.0,
        "waiting_requests": 82110.49956786491
      },
      "constant": 13168.752861258823,
      "dependent_columns": [
        1
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 130.2503559407778,
    "max_unexplained_share": 0.5865014263825753,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "waiting_requests",
      "waiting_blocks",
      "priority_queue_work"
    ],
    "raw_files": [
      "run.2270844.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 20,
        "instructions_per_call": 3735.75,
        "state": {
          "priority_queue_work": 0,
          "waiting_blocks": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 1396.4999999999993,
        "unexplained_share": 0.37382051796827925
      },
      {
        "calls": 1,
        "instructions_per_call": 236262.0,
        "state": {
          "priority_queue_work": 1,
          "waiting_blocks": 1,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 138568.0,
        "unexplained_share": 0.5865014263825753
      },
      {
        "calls": 1,
        "instructions_per_call": 325274.0,
        "state": {
          "priority_queue_work": 4,
          "waiting_blocks": 2,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 149660.0,
        "unexplained_share": 0.4601044042868474
      },
      {
        "calls": 1,
        "instructions_per_call": 394326.0,
        "state": {
          "priority_queue_work": 6,
          "waiting_blocks": 3,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 139721.0,
        "unexplained_share": 0.3543286519275929
      },
      {
        "calls": 1,
        "instructions_per_call": 520501.0,
        "state": {
          "priority_queue_work": 12,
          "waiting_blocks": 4,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 181893.0,
        "unexplained_share": 0.34945754186831535
      },
      {
        "calls": 1,
        "instructions_per_call": 655118.0,
        "state": {
          "priority_queue_work": 15,
          "waiting_blocks": 5,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 229530.0,
        "unexplained_share": 0.35036436184015707
      },
      {
        "calls": 1,
        "instructions_per_call": 783451.0,
        "state": {
          "priority_queue_work": 18,
          "waiting_blocks": 6,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 272758.0,
        "unexplained_share": 0.3481494056424716
      },
      {
        "calls": 1,
        "instructions_per_call": 915693.0,
        "state": {
          "priority_queue_work": 21,
          "waiting_blocks": 7,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 318923.0,
        "unexplained_share": 0.3482859429961789
      },
      {
        "calls": 1,
        "instructions_per_call": 1044726.0,
        "state": {
          "priority_queue_work": 32,
          "waiting_blocks": 8,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 362451.0,
        "unexplained_share": 0.3469340286352594
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e0089cc65a4a7aeff1ced94a1a01c7c91a1294c6c5c4a8f7f4abd224aecec46b",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 58.65014263825753,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 58.65014263825753,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e0089cc65a4a7aeff1ced94a1a01c7c91a1294c6c5c4a8f7f4abd224aecec46b"
  }
}