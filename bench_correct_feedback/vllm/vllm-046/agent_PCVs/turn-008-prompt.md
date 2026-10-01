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
    "hypothesis": "Separate correlated regressors consistently leave sampling and decoding work unexplained. A combined work measure should stabilize attribution while preserving the observed cost ratios; the admission indicator accounts for the isolated initialization event.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "6 * sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests)) + 3 * len(self.engine_core.engine_core.scheduler.requests) + (len(self.engine_core.engine_core.scheduler.requests) + 1) * int(sum((self.engine_core.engine_core.scheduler.requests[k].sampling_params.temperature > 0 for k in self.engine_core.engine_core.scheduler.requests)) > 0)",
        "name": "effective_token_work",
        "rationale": "Combines token execution, per-request overhead, and batch-wide sampling into one integer work measure. Relative weights approximate the observed prefill, greedy-decode, and sampled-decode cost ratios."
      },
      {
        "expression": "int(len(self.engine_core.engine_core.scheduler.waiting) == 2 and len(self.engine_core.engine_core.scheduler.running) == 0)",
        "name": "two_request_admission",
        "rationale": "Separates the unusually expensive first mixed-sampling prefill using the established workload-specific entry-state proxy."
      }
    ]
  },
  "case_id": "vllm-046",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-046",
    "distinct_states": 17,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "effective_token_work": 221.64562436047035,
        "two_request_admission": 15803094123.770119
      },
      "constant": 2846044.7873703586,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 73.705431567505,
    "max_unexplained_share": 0.9998974816787642,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "effective_token_work",
      "two_request_admission"
    ],
    "raw_files": [
      "run.2321733.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 147978751.0,
        "state": {
          "effective_token_work": 9,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 145343064.25,
        "unexplained_share": 0.9821887485048445
      },
      {
        "calls": 1,
        "instructions_per_call": 176839121.0,
        "state": {
          "effective_token_work": 11,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 174193463.0,
        "unexplained_share": 0.985039181460306
      },
      {
        "calls": 2,
        "instructions_per_call": 294796414.0,
        "state": {
          "effective_token_work": 18,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 292087539.0,
        "unexplained_share": 0.9908110313716367
      },
      {
        "calls": 5,
        "instructions_per_call": 330766925.2,
        "state": {
          "effective_token_work": 21,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 328016728.60000134,
        "unexplained_share": 0.9916853941840293
      },
      {
        "calls": 1,
        "instructions_per_call": 435680223.0,
        "state": {
          "effective_token_work": 27,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 432940252.0,
        "unexplained_share": 0.9937110503177464
      },
      {
        "calls": 2,
        "instructions_per_call": 494620085.0,
        "state": {
          "effective_token_work": 31,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 491759572.5,
        "unexplained_share": 0.9942167481937172
      },
      {
        "calls": 2,
        "instructions_per_call": 652887531.5,
        "state": {
          "effective_token_work": 41,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 650019183.5,
        "unexplained_share": 0.9956066736434528
      },
      {
        "calls": 2,
        "instructions_per_call": 813677014.5,
        "state": {
          "effective_token_work": 51,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 810774870.0,
        "unexplained_share": 0.9964332966910914
      },
      {
        "calls": 1,
        "instructions_per_call": 972564568.0,
        "state": {
          "effective_token_work": 61,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 969645028.0,
        "unexplained_share": 0.9969981016211563
      },
      {
        "calls": 1,
        "instructions_per_call": 985596058.0,
        "state": {
          "effective_token_work": 63,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 982859525.0,
        "unexplained_share": 0.9972234740817115
      },
      {
        "calls": 1,
        "instructions_per_call": 18865711735.0,
        "state": {
          "effective_token_work": 129,
          "two_request_admission": 1
        },
        "unexplained_instructions_per_call": 3059777272.0,
        "unexplained_share": 0.16218721641566522
      },
      {
        "calls": 1,
        "instructions_per_call": 6335993444.0,
        "state": {
          "effective_token_work": 409,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 6332995380.0,
        "unexplained_share": 0.9995268202174611
      },
      {
        "calls": 1,
        "instructions_per_call": 8071569747.0,
        "state": {
          "effective_token_work": 521,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 8068502306.0,
        "unexplained_share": 0.9996199697089726
      },
      {
        "calls": 1,
        "instructions_per_call": 21685722894.0,
        "state": {
          "effective_token_work": 1401,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 21682461034.0,
        "unexplained_share": 0.9998495849081931
      },
      {
        "calls": 1,
        "instructions_per_call": 25464083497.0,
        "state": {
          "effective_token_work": 1645,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 25460741851.0,
        "unexplained_share": 0.9998687702229537
      },
      {
        "calls": 1,
        "instructions_per_call": 30354248861.0,
        "state": {
          "effective_token_work": 1961,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 30350784252.0,
        "unexplained_share": 0.9998858608224547
      },
      {
        "calls": 1,
        "instructions_per_call": 34689945730.0,
        "state": {
          "effective_token_work": 2241,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 34686389375.0,
        "unexplained_share": 0.9998974816787642
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 99.98974816787643,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 99.98974816787643,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}