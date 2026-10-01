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

This is iteration 10. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Queue removal introduces a batch-size-by-completion interaction. Earlier additive predictors and combined regime terms did not represent this conditional scan independently; this candidate tests that structural cost directly.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "len(scheduler_output.num_scheduled_tokens)",
        "name": "scheduled_requests",
        "rationale": "Captures the main request-processing loop."
      },
      {
        "expression": "len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens])",
        "name": "finishing_requests",
        "rationale": "Captures completion and resource release."
      },
      {
        "expression": "len(scheduler_output.scheduled_new_reqs)",
        "name": "new_requests",
        "rationale": "Captures prefill completion work."
      },
      {
        "expression": "len(self.running) if len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens]) > 0 else 0",
        "name": "cleanup_scan_requests",
        "rationale": "Measures the full running-queue scan performed only when at least one request stops."
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
        "cleanup_scan_requests": 3921.1415561512495,
        "finishing_requests": 8607.984551354399,
        "new_requests": 12247.736606471039,
        "scheduled_requests": 10376.869610609485
      },
      "constant": 29486.46659181403,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 122.57012050785124,
    "max_unexplained_share": 0.598148170301341,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "scheduled_requests",
      "finishing_requests",
      "new_requests",
      "cleanup_scan_requests"
    ],
    "raw_files": [
      "run.2284806.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 70111.0,
        "state": {
          "cleanup_scan_requests": 1,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 24446.0,
        "unexplained_share": 0.3486756714352955
      },
      {
        "calls": 1,
        "instructions_per_call": 167186.0,
        "state": {
          "cleanup_scan_requests": 1,
          "finishing_requests": 1,
          "new_requests": 1,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 100002.0,
        "unexplained_share": 0.598148170301341
      },
      {
        "calls": 1,
        "instructions_per_call": 60523.0,
        "state": {
          "cleanup_scan_requests": 0,
          "finishing_requests": 0,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 20299.0,
        "unexplained_share": 0.3353931563207376
      },
      {
        "calls": 1,
        "instructions_per_call": 147765.0,
        "state": {
          "cleanup_scan_requests": 0,
          "finishing_requests": 0,
          "new_requests": 2,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 72355.0,
        "unexplained_share": 0.489662640002707
      },
      {
        "calls": 4,
        "instructions_per_call": 102365.25,
        "state": {
          "cleanup_scan_requests": 2,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 39317.0,
        "unexplained_share": 0.38408541961261267
      },
      {
        "calls": 2,
        "instructions_per_call": 112162.5,
        "state": {
          "cleanup_scan_requests": 2,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 39352.5,
        "unexplained_share": 0.35085255767301904
      },
      {
        "calls": 2,
        "instructions_per_call": 115684.0,
        "state": {
          "cleanup_scan_requests": 3,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 39008.5,
        "unexplained_share": 0.33719874831437363
      },
      {
        "calls": 1,
        "instructions_per_call": 172102.0,
        "state": {
          "cleanup_scan_requests": 3,
          "finishing_requests": 1,
          "new_requests": 3,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 56879.0,
        "unexplained_share": 0.33049586872900955
      },
      {
        "calls": 1,
        "instructions_per_call": 133006.0,
        "state": {
          "cleanup_scan_requests": 3,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 45583.0,
        "unexplained_share": 0.34271386253251734
      },
      {
        "calls": 1,
        "instructions_per_call": 213275.0,
        "state": {
          "cleanup_scan_requests": 4,
          "finishing_requests": 1,
          "new_requests": 4,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 67909.0,
        "unexplained_share": 0.31841050287187905
      },
      {
        "calls": 2,
        "instructions_per_call": 155768.0,
        "state": {
          "cleanup_scan_requests": 4,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 53403.0,
        "unexplained_share": 0.34283678290791436
      },
      {
        "calls": 1,
        "instructions_per_call": 164475.0,
        "state": {
          "cleanup_scan_requests": 5,
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 55162.0,
        "unexplained_share": 0.33538227694178446
      },
      {
        "calls": 1,
        "instructions_per_call": 177770.0,
        "state": {
          "cleanup_scan_requests": 5,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 60551.0,
        "unexplained_share": 0.34061427687461326
      },
      {
        "calls": 1,
        "instructions_per_call": 275098.0,
        "state": {
          "cleanup_scan_requests": 5,
          "finishing_requests": 2,
          "new_requests": 5,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 90065.0,
        "unexplained_share": 0.32739242015572634
      },
      {
        "calls": 1,
        "instructions_per_call": 297300.0,
        "state": {
          "cleanup_scan_requests": 6,
          "finishing_requests": 1,
          "new_requests": 6,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 93502.0,
        "unexplained_share": 0.3145038681466532
      },
      {
        "calls": 1,
        "instructions_per_call": 200045.0,
        "state": {
          "cleanup_scan_requests": 6,
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 67933.0,
        "unexplained_share": 0.3395885925666725
      },
      {
        "calls": 1,
        "instructions_per_call": 353660.0,
        "state": {
          "cleanup_scan_requests": 7,
          "finishing_requests": 2,
          "new_requests": 7,
          "scheduled_requests": 7
        },
        "unexplained_instructions_per_call": 112714.0,
        "unexplained_share": 0.31870723293558784
      },
      {
        "calls": 1,
        "instructions_per_call": 394174.0,
        "state": {
          "cleanup_scan_requests": 8,
          "finishing_requests": 2,
          "new_requests": 8,
          "scheduled_requests": 8
        },
        "unexplained_instructions_per_call": 124844.0,
        "unexplained_share": 0.31672307153693546
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 59.8148170301341,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 59.8148170301341,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89"
  }
}