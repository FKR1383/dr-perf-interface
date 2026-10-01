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
    "hypothesis": "Most calls follow a linear token-and-request cost model with an additional sampling cost. The extreme residual occurs at the first mixed-sampling prefill; a workload-specific entry-state indicator separates that likely initialization event.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests)",
        "name": "active_requests",
        "rationale": "Models the approximately linear per-request decoding and output cost."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens - 1) for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "additional_pending_tokens",
        "rationale": "Separates additional prefill positions from the baseline one-token cost per active request."
      },
      {
        "expression": "sum((self.engine_core.engine_core.scheduler.requests[k].sampling_params.temperature > 0 for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "sampled_requests",
        "rationale": "Captures extra random-sampling work that can explain differences between equally sized decoding batches."
      },
      {
        "expression": "int(len(self.engine_core.engine_core.scheduler.waiting) == 2 and len(self.engine_core.engine_core.scheduler.running) == 0)",
        "name": "two_request_admission",
        "rationale": "Isolates the observed costly two-request admission, which is the fixed workload's first batch containing random sampling and may incur lazy initialization. This is a workload-specific proxy."
      }
    ]
  },
  "case_id": "vllm-046",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-046",
    "distinct_states": 18,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_requests": 132847839.64140648,
        "additional_pending_tokens": 90125307.31948994,
        "sampled_requests": 2263.3945950241996,
        "two_request_admission": 15952635558.773142
      },
      "constant": 4842304.017602505,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 80.86591496272013,
    "max_unexplained_share": 0.22443777774984486,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "active_requests",
      "additional_pending_tokens",
      "sampled_requests",
      "two_request_admission"
    ],
    "raw_files": [
      "run.2319447.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 147984726.25,
        "state": {
          "active_requests": 1,
          "additional_pending_tokens": 0,
          "sampled_requests": 0,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 10858788.0,
        "unexplained_share": 0.07337776184858132
      },
      {
        "calls": 1,
        "instructions_per_call": 176852259.0,
        "state": {
          "active_requests": 1,
          "additional_pending_tokens": 0,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 39692328.0,
        "unexplained_share": 0.22443777774984486
      },
      {
        "calls": 1,
        "instructions_per_call": 985581735.0,
        "state": {
          "active_requests": 1,
          "additional_pending_tokens": 9,
          "sampled_requests": 0,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 37247369.0,
        "unexplained_share": 0.03779226793402376
      },
      {
        "calls": 2,
        "instructions_per_call": 294795683.0,
        "state": {
          "active_requests": 2,
          "additional_pending_tokens": 0,
          "sampled_requests": 0,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 24614073.5,
        "unexplained_share": 0.083495366178751
      },
      {
        "calls": 5,
        "instructions_per_call": 330769081.6,
        "state": {
          "active_requests": 2,
          "additional_pending_tokens": 0,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 60522728.80000015,
        "unexplained_share": 0.1829757742387496
      },
      {
        "calls": 1,
        "instructions_per_call": 18865240446.0,
        "state": {
          "active_requests": 2,
          "additional_pending_tokens": 18,
          "sampled_requests": 1,
          "two_request_admission": 1
        },
        "unexplained_instructions_per_call": 1020047044.0,
        "unexplained_share": 0.05407018515983351
      },
      {
        "calls": 1,
        "instructions_per_call": 435667774.0,
        "state": {
          "active_requests": 3,
          "additional_pending_tokens": 0,
          "sampled_requests": 0,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 32538734.0,
        "unexplained_share": 0.07468703434557912
      },
      {
        "calls": 2,
        "instructions_per_call": 494628077.0,
        "state": {
          "active_requests": 3,
          "additional_pending_tokens": 0,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 91243658.5,
        "unexplained_share": 0.18446922595540408
      },
      {
        "calls": 1,
        "instructions_per_call": 6335964638.0,
        "state": {
          "active_requests": 3,
          "additional_pending_tokens": 63,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 254587227.0,
        "unexplained_share": 0.04018128912417077
      },
      {
        "calls": 1,
        "instructions_per_call": 652257946.0,
        "state": {
          "active_requests": 4,
          "additional_pending_tokens": 0,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 115974482.0,
        "unexplained_share": 0.1778046288454108
      },
      {
        "calls": 1,
        "instructions_per_call": 653492214.0,
        "state": {
          "active_requests": 4,
          "additional_pending_tokens": 0,
          "sampled_requests": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 117199384.0,
        "unexplained_share": 0.17934319872401724
      },
      {
        "calls": 1,
        "instructions_per_call": 8071566656.0,
        "state": {
          "active_requests": 4,
          "additional_pending_tokens": 80,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 325080557.0,
        "unexplained_share": 0.04027477822516046
      },
      {
        "calls": 2,
        "instructions_per_call": 813666014.5,
        "state": {
          "active_requests": 5,
          "additional_pending_tokens": 0,
          "sampled_requests": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 144425664.0,
        "unexplained_share": 0.17749993415756704
      },
      {
        "calls": 1,
        "instructions_per_call": 21685740560.0,
        "state": {
          "active_requests": 5,
          "additional_pending_tokens": 225,
          "sampled_requests": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 738157315.0,
        "unexplained_share": 0.0340388336269942
      },
      {
        "calls": 1,
        "instructions_per_call": 972549173.0,
        "state": {
          "active_requests": 6,
          "additional_pending_tokens": 0,
          "sampled_requests": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 170385472.0,
        "unexplained_share": 0.17519471172281795
      },
      {
        "calls": 1,
        "instructions_per_call": 25464058473.0,
        "state": {
          "active_requests": 6,
          "additional_pending_tokens": 264,
          "sampled_requests": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 868638845.0,
        "unexplained_share": 0.034112348819848703
      },
      {
        "calls": 1,
        "instructions_per_call": 30354229940.0,
        "state": {
          "active_requests": 7,
          "additional_pending_tokens": 315,
          "sampled_requests": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1029426052.0,
        "unexplained_share": 0.03391375943434657
      },
      {
        "calls": 1,
        "instructions_per_call": 34689948820.0,
        "state": {
          "active_requests": 8,
          "additional_pending_tokens": 360,
          "sampled_requests": 3,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1176544712.0,
        "unexplained_share": 0.033916011756168395
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 22.443777774984486,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 22.443777774984486,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}