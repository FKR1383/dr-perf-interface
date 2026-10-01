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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Sampling-option predictors explain little additional instruction work. A quadratic batch-size term tests whether the persistent residual instead reflects nonlinear batch processing; retaining raw request and token counts preserves the strongest existing attribution.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests)",
        "name": "active_requests",
        "rationale": "Retains the request cardinality that explains substantial per-request work."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "pending_tokens",
        "rationale": "Retains the successful predictor for model token execution."
      },
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests) ** 2",
        "name": "request_pairs",
        "rationale": "Tests nonlinear batch-size effects in execution and sampling that the previous sampling-option features did not explain."
      },
      {
        "expression": "int(len(self.engine_core.engine_core.scheduler.waiting) == 2 and len(self.engine_core.engine_core.scheduler.running) == 0)",
        "name": "two_request_admission",
        "rationale": "Separates the expensive first mixed-sampling admission using the established workload-specific proxy."
      }
    ]
  },
  "case_id": "vllm-046",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-046",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_requests": 42944479.61494905,
        "pending_tokens": 90124543.14471151,
        "request_pairs": -14815.451555411404,
        "two_request_admission": 16084622124.741669
      },
      "constant": 5772137.324654721,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 79.20300575345755,
    "max_unexplained_share": 0.17640139676788438,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "active_requests",
      "pending_tokens",
      "request_pairs",
      "two_request_admission"
    ],
    "raw_files": [
      "run.2324000.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 153769217.0,
        "state": {
          "active_requests": 1,
          "pending_tokens": 1,
          "request_pairs": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 15376361.600000057,
        "unexplained_share": 0.09999635752843859
      },
      {
        "calls": 1,
        "instructions_per_call": 985567034.0,
        "state": {
          "active_requests": 1,
          "pending_tokens": 10,
          "request_pairs": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 35944697.0,
        "unexplained_share": 0.03647108289947125
      },
      {
        "calls": 7,
        "instructions_per_call": 320500498.5714286,
        "state": {
          "active_requests": 2,
          "pending_tokens": 2,
          "request_pairs": 4,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 48931965.71428586,
        "unexplained_share": 0.15267360248233935
      },
      {
        "calls": 1,
        "instructions_per_call": 18865419206.0,
        "state": {
          "active_requests": 2,
          "pending_tokens": 20,
          "request_pairs": 4,
          "two_request_admission": 1
        },
        "unexplained_instructions_per_call": 886886425.0,
        "unexplained_share": 0.04701122277303717
      },
      {
        "calls": 3,
        "instructions_per_call": 474975705.0,
        "state": {
          "active_requests": 3,
          "pending_tokens": 3,
          "request_pairs": 9,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 70276628.33333339,
        "unexplained_share": 0.14795836417219146
      },
      {
        "calls": 1,
        "instructions_per_call": 6335954385.0,
        "state": {
          "active_requests": 3,
          "pending_tokens": 66,
          "request_pairs": 9,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 253150690.0,
        "unexplained_share": 0.03995462634631957
      },
      {
        "calls": 2,
        "instructions_per_call": 652895023.0,
        "state": {
          "active_requests": 4,
          "pending_tokens": 4,
          "request_pairs": 16,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 115171594.0,
        "unexplained_share": 0.17640139676788438
      },
      {
        "calls": 1,
        "instructions_per_call": 8071555063.0,
        "state": {
          "active_requests": 4,
          "pending_tokens": 84,
          "request_pairs": 16,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 323623143.0,
        "unexplained_share": 0.0400942743342591
      },
      {
        "calls": 2,
        "instructions_per_call": 813694107.5,
        "state": {
          "active_requests": 5,
          "pending_tokens": 5,
          "request_pairs": 25,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 142995738.0,
        "unexplained_share": 0.1757364796942443
      },
      {
        "calls": 1,
        "instructions_per_call": 21685717126.0,
        "state": {
          "active_requests": 5,
          "pending_tokens": 230,
          "request_pairs": 25,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 736790582.0,
        "unexplained_share": 0.03397584583986978
      },
      {
        "calls": 1,
        "instructions_per_call": 972574629.0,
        "state": {
          "active_requests": 6,
          "pending_tokens": 6,
          "request_pairs": 36,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 168943593.0,
        "unexplained_share": 0.173707588047724
      },
      {
        "calls": 1,
        "instructions_per_call": 25464077266.0,
        "state": {
          "active_requests": 6,
          "pending_tokens": 270,
          "request_pairs": 36,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 867322718.0,
        "unexplained_share": 0.03406063800937573
      },
      {
        "calls": 1,
        "instructions_per_call": 30354247840.0,
        "state": {
          "active_requests": 7,
          "pending_tokens": 322,
          "request_pairs": 49,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1028115666.0,
        "unexplained_share": 0.03387056966192314
      },
      {
        "calls": 1,
        "instructions_per_call": 34689929799.0,
        "state": {
          "active_requests": 8,
          "pending_tokens": 368,
          "request_pairs": 64,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1175210756.0,
        "unexplained_share": 0.033877576657242975
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.64013967678844,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.64013967678844,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}