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

This is iteration 6. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Cleanup has a fixed branch cost in addition to its per-finishing-request cost. Combining that branch indicator with the small-prefill term tests both effects within four expressions.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "len(scheduler_output.num_scheduled_tokens)",
        "name": "scheduled_requests",
        "rationale": "Captures per-request processing."
      },
      {
        "expression": "len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens])",
        "name": "finishing_requests",
        "rationale": "Captures per-request completion and resource release."
      },
      {
        "expression": "len(scheduler_output.scheduled_new_reqs)",
        "name": "new_requests",
        "rationale": "Captures prefill completion work."
      },
      {
        "expression": "2 * (len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens]) > 0) + (3 * max(0, 3 - len(scheduler_output.scheduled_new_reqs)) if scheduler_output.scheduled_new_reqs else 0)",
        "name": "cleanup_and_small_prefill",
        "rationale": "Combines the fixed cost of stopped-request queue cleanup with the observed excess cost of small prefill batches."
      }
    ]
  },
  "case_id": "vllm-038",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-038",
    "distinct_states": 18,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "cleanup_and_small_prefill": 2756.888477856306,
        "finishing_requests": 13660.62546308783,
        "new_requests": 13781.747761569954,
        "scheduled_requests": 16131.639730325325
      },
      "constant": 28416.558360267816,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 100.48737182095647,
    "max_unexplained_share": 0.4511046573151948,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "scheduled_requests",
      "finishing_requests",
      "new_requests",
      "cleanup_and_small_prefill"
    ],
    "raw_files": [
      "run.2281522.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 69930.6,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 15200.799999999997,
        "unexplained_share": 0.21736979233697404
      },
      {
        "calls": 1,
        "instructions_per_call": 170098.0,
        "state": {
          "cleanup_and_small_prefill": 8,
          "finishing_requests": 1,
          "new_requests": 1,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 76732.0,
        "unexplained_share": 0.4511046573151948
      },
      {
        "calls": 1,
        "instructions_per_call": 60942.0,
        "state": {
          "cleanup_and_small_prefill": 0,
          "finishing_requests": 0,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 12807.0,
        "unexplained_share": 0.21015063503002857
      },
      {
        "calls": 1,
        "instructions_per_call": 147966.0,
        "state": {
          "cleanup_and_small_prefill": 3,
          "finishing_requests": 0,
          "new_requests": 2,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 60127.0,
        "unexplained_share": 0.40635686576645985
      },
      {
        "calls": 4,
        "instructions_per_call": 101800.25,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 26996.5,
        "unexplained_share": 0.26519090080820035
      },
      {
        "calls": 2,
        "instructions_per_call": 111709.5,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 23905.5,
        "unexplained_share": 0.2139970190538853
      },
      {
        "calls": 2,
        "instructions_per_call": 115622.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 24434.0,
        "unexplained_share": 0.21132656414869141
      },
      {
        "calls": 1,
        "instructions_per_call": 173188.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 3,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 36478.0,
        "unexplained_share": 0.2106266023050096
      },
      {
        "calls": 1,
        "instructions_per_call": 132641.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 27260.0,
        "unexplained_share": 0.20551714778989905
      },
      {
        "calls": 1,
        "instructions_per_call": 213119.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 4,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 42417.0,
        "unexplained_share": 0.19902965010158644
      },
      {
        "calls": 2,
        "instructions_per_call": 155208.5,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 32139.5,
        "unexplained_share": 0.20707306623026445
      },
      {
        "calls": 1,
        "instructions_per_call": 164151.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 35298.0,
        "unexplained_share": 0.21503371895389
      },
      {
        "calls": 1,
        "instructions_per_call": 176526.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 35690.0,
        "unexplained_share": 0.20217984886079104
      },
      {
        "calls": 1,
        "instructions_per_call": 274710.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 5,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 55791.0,
        "unexplained_share": 0.20309053183356995
      },
      {
        "calls": 1,
        "instructions_per_call": 297369.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 1,
          "new_requests": 6,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 58862.0,
        "unexplained_share": 0.19794262347453837
      },
      {
        "calls": 1,
        "instructions_per_call": 198767.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 40114.0,
        "unexplained_share": 0.20181418444711646
      },
      {
        "calls": 1,
        "instructions_per_call": 352708.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 7,
          "scheduled_requests": 7
        },
        "unexplained_instructions_per_call": 68297.0,
        "unexplained_share": 0.19363609558048017
      },
      {
        "calls": 1,
        "instructions_per_call": 393334.0,
        "state": {
          "cleanup_and_small_prefill": 2,
          "finishing_requests": 2,
          "new_requests": 8,
          "scheduled_requests": 8
        },
        "unexplained_instructions_per_call": 75629.0,
        "unexplained_share": 0.19227679275119872
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 45.110465731519476,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 45.110465731519476,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89"
  }
}