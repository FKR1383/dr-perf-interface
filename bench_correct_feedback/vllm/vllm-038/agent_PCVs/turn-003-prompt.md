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

This is iteration 3. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Request count, finishing count, and new-request count explain the dominant work. Removing redundant block estimation and repeated indexed scans should substantially reduce observation overhead, which appears to dominate the previous unexplained instructions.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(scheduler_output.num_scheduled_tokens)",
        "name": "scheduled_requests",
        "rationale": "Measures the main request-processing loop with constant-time observation."
      },
      {
        "expression": "len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens])",
        "name": "finishing_requests",
        "rationale": "Predicts cleanup for the workload's single-token outputs using one short scan."
      },
      {
        "expression": "len(scheduler_output.scheduled_new_reqs)",
        "name": "new_requests",
        "rationale": "Provides a constant-time proxy for prefill completion and first-output statistics."
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
        "finishing_requests": 10554.482436323362,
        "new_requests": 11158.620276854936,
        "scheduled_requests": 13560.618863049089
      },
      "constant": 27614.046667281917,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 122.4379732273519,
    "max_unexplained_share": 0.6119383262557887,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "scheduled_requests",
      "finishing_requests",
      "new_requests"
    ],
    "raw_files": [
      "run.2278772.json"
    ],
    "required_states": 5,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 70286.8,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 25663.59999999999,
        "unexplained_share": 0.36512688015388367
      },
      {
        "calls": 1,
        "instructions_per_call": 166489.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 1,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 101881.0,
        "unexplained_share": 0.6119383262557887
      },
      {
        "calls": 1,
        "instructions_per_call": 61321.0,
        "state": {
          "finishing_requests": 0,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 21685.0,
        "unexplained_share": 0.353630893168735
      },
      {
        "calls": 1,
        "instructions_per_call": 148300.0,
        "state": {
          "finishing_requests": 0,
          "new_requests": 2,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 76044.0,
        "unexplained_share": 0.512771409305462
      },
      {
        "calls": 4,
        "instructions_per_call": 102761.25,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 41346.0,
        "unexplained_share": 0.40235010765244683
      },
      {
        "calls": 2,
        "instructions_per_call": 111815.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 40524.0,
        "unexplained_share": 0.36242006886374817
      },
      {
        "calls": 2,
        "instructions_per_call": 116011.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 41103.5,
        "unexplained_share": 0.3543069191714579
      },
      {
        "calls": 1,
        "instructions_per_call": 173797.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 3,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 62042.0,
        "unexplained_share": 0.35697969470128943
      },
      {
        "calls": 1,
        "instructions_per_call": 132808.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 47062.0,
        "unexplained_share": 0.35436118306126135
      },
      {
        "calls": 1,
        "instructions_per_call": 214921.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 4,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 74533.0,
        "unexplained_share": 0.34679254237603585
      },
      {
        "calls": 2,
        "instructions_per_call": 155669.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 55186.5,
        "unexplained_share": 0.35451181673936366
      },
      {
        "calls": 1,
        "instructions_per_call": 164708.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 58307.0,
        "unexplained_share": 0.3540022342569881
      },
      {
        "calls": 1,
        "instructions_per_call": 177419.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 62168.0,
        "unexplained_share": 0.35040215534976527
      },
      {
        "calls": 1,
        "instructions_per_call": 275954.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 5,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 96779.0,
        "unexplained_share": 0.35070700189161963
      },
      {
        "calls": 1,
        "instructions_per_call": 298517.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 6,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 102342.0,
        "unexplained_share": 0.34283474642985157
      },
      {
        "calls": 1,
        "instructions_per_call": 199567.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 69625.0,
        "unexplained_share": 0.3488803259055856
      },
      {
        "calls": 1,
        "instructions_per_call": 355803.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 7,
          "scheduled_requests": 7
        },
        "unexplained_instructions_per_call": 122487.0,
        "unexplained_share": 0.34425510746115123
      },
      {
        "calls": 1,
        "instructions_per_call": 394203.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 8,
          "scheduled_requests": 8
        },
        "unexplained_instructions_per_call": 133818.0,
        "unexplained_share": 0.3394646920495278
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 61.19383262557887,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 61.19383262557887,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89"
  }
}