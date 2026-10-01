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

This is iteration 8. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The remaining sampled-decode residual may come from selection work whose extent depends on top-k. Preserve the successful primitive model-work features and replace sampling presence with batch size times maximum top-k.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests)",
        "name": "active_requests",
        "rationale": "Explains shared per-request model and output work."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "pending_tokens",
        "rationale": "Explains the dominant model execution work across prefill and decoding."
      },
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests) * max((self.engine_core.engine_core.scheduler.requests[k].sampling_params.top_k for k in self.engine_core.engine_core.scheduler.requests), default=0)",
        "name": "batch_top_k_extent",
        "rationale": "Tests whether bounded selection work depends on the batch's largest top-k setting as well as batch size, which sampling presence alone omitted."
      },
      {
        "expression": "int(len(self.engine_core.engine_core.scheduler.waiting) == 2 and len(self.engine_core.engine_core.scheduler.running) == 0)",
        "name": "two_request_admission",
        "rationale": "Retains the workload-specific proxy for the expensive first mixed-sampling admission."
      }
    ]
  },
  "case_id": "vllm-046",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-046",
    "distinct_states": 20,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_requests": 42805610.661340594,
        "batch_top_k_extent": -70.25373409475422,
        "pending_tokens": 90124462.27303457,
        "two_request_admission": 15939006061.135645
      },
      "constant": 4205930.322639603,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 79.68604869954288,
    "max_unexplained_share": 0.22594566726142057,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "active_requests",
      "pending_tokens",
      "batch_top_k_extent",
      "two_request_admission"
    ],
    "raw_files": [
      "run.2323201.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 147932670.25,
        "state": {
          "active_requests": 1,
          "batch_top_k_extent": 0,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 11110566.75,
        "unexplained_share": 0.07510556478987102
      },
      {
        "calls": 1,
        "instructions_per_call": 176799739.0,
        "state": {
          "active_requests": 1,
          "batch_top_k_extent": 7,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 39947135.0,
        "unexplained_share": 0.22594566726142057
      },
      {
        "calls": 1,
        "instructions_per_call": 985565248.0,
        "state": {
          "active_requests": 1,
          "batch_top_k_extent": 0,
          "pending_tokens": 10,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 37524195.0,
        "unexplained_share": 0.038073780580380204
      },
      {
        "calls": 2,
        "instructions_per_call": 294746095.0,
        "state": {
          "active_requests": 2,
          "batch_top_k_extent": 0,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 24883893.5,
        "unexplained_share": 0.08442484539108143
      },
      {
        "calls": 3,
        "instructions_per_call": 327613650.0,
        "state": {
          "active_requests": 2,
          "batch_top_k_extent": 14,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 57797303.33333344,
        "unexplained_share": 0.1764190940558595
      },
      {
        "calls": 2,
        "instructions_per_call": 335361233.0,
        "state": {
          "active_requests": 2,
          "batch_top_k_extent": 32,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 65268370.0,
        "unexplained_share": 0.19462109384599025
      },
      {
        "calls": 1,
        "instructions_per_call": 18864480836.0,
        "state": {
          "active_requests": 2,
          "batch_top_k_extent": 14,
          "pending_tokens": 20,
          "two_request_admission": 1
        },
        "unexplained_instructions_per_call": 1033255938.0,
        "unexplained_share": 0.054772561565976825
      },
      {
        "calls": 1,
        "instructions_per_call": 435723149.0,
        "state": {
          "active_requests": 3,
          "batch_top_k_extent": 0,
          "pending_tokens": 3,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 32887413.0,
        "unexplained_share": 0.07547777315820325
      },
      {
        "calls": 2,
        "instructions_per_call": 494579268.5,
        "state": {
          "active_requests": 3,
          "batch_top_k_extent": 30,
          "pending_tokens": 3,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 91539142.0,
        "unexplained_share": 0.185084874822245
      },
      {
        "calls": 1,
        "instructions_per_call": 6335922673.0,
        "state": {
          "active_requests": 3,
          "batch_top_k_extent": 21,
          "pending_tokens": 66,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 254944765.0,
        "unexplained_share": 0.040237985555983125
      },
      {
        "calls": 1,
        "instructions_per_call": 652204643.0,
        "state": {
          "active_requests": 4,
          "batch_top_k_extent": 64,
          "pending_tokens": 4,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 116265867.0,
        "unexplained_share": 0.1782659296401237
      },
      {
        "calls": 1,
        "instructions_per_call": 653459752.0,
        "state": {
          "active_requests": 4,
          "batch_top_k_extent": 76,
          "pending_tokens": 4,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 117513698.0,
        "unexplained_share": 0.17983310776269507
      },
      {
        "calls": 1,
        "instructions_per_call": 8071518035.0,
        "state": {
          "active_requests": 4,
          "batch_top_k_extent": 40,
          "pending_tokens": 84,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 325446464.0,
        "unexplained_share": 0.04032035393946809
      },
      {
        "calls": 1,
        "instructions_per_call": 813816604.0,
        "state": {
          "active_requests": 5,
          "batch_top_k_extent": 50,
          "pending_tokens": 5,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 144930474.0,
        "unexplained_share": 0.17808738883877576
      },
      {
        "calls": 1,
        "instructions_per_call": 813450030.0,
        "state": {
          "active_requests": 5,
          "batch_top_k_extent": 80,
          "pending_tokens": 5,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 144548983.0,
        "unexplained_share": 0.17769866330941067
      },
      {
        "calls": 1,
        "instructions_per_call": 21685685739.0,
        "state": {
          "active_requests": 5,
          "batch_top_k_extent": 65,
          "pending_tokens": 230,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 738642243.0,
        "unexplained_share": 0.034061281339681594
      },
      {
        "calls": 1,
        "instructions_per_call": 972510003.0,
        "state": {
          "active_requests": 6,
          "batch_top_k_extent": 114,
          "pending_tokens": 6,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 170695148.0,
        "unexplained_share": 0.17552019770844454
      },
      {
        "calls": 1,
        "instructions_per_call": 25464012093.0,
        "state": {
          "active_requests": 6,
          "batch_top_k_extent": 78,
          "pending_tokens": 270,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 869164226.0,
        "unexplained_share": 0.034133043246509114
      },
      {
        "calls": 1,
        "instructions_per_call": 30354105015.0,
        "state": {
          "active_requests": 7,
          "batch_top_k_extent": 112,
          "pending_tokens": 322,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1029948278.0,
        "unexplained_share": 0.03393110346989422
      },
      {
        "calls": 1,
        "instructions_per_call": 34689904591.0,
        "state": {
          "active_requests": 8,
          "batch_top_k_extent": 152,
          "pending_tokens": 368,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1177160898.0,
        "unexplained_share": 0.033933817687852745
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 22.594566726142055,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 22.594566726142055,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}