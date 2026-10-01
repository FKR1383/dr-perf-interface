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

This is iteration 5. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Shared token and request features avoid the fitting failure of disjoint prefill/decode features. Batch-wide sampling extent should explain the residual that sampled-request count missed; positive-baseline regime features test whether sparse feature support contributed to unstable attribution.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests)",
        "name": "active_requests",
        "rationale": "Restores the shared request-count feature, which explained most decoding work in iteration 2."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "pending_tokens",
        "rationale": "Represents model token work in both prefill and decoding without mutually exclusive regime features."
      },
      {
        "expression": "1 + (len(self.engine_core.engine_core.scheduler.requests) + 1) * int(sum((self.engine_core.engine_core.scheduler.requests[k].sampling_params.temperature > 0 for k in self.engine_core.engine_core.scheduler.requests)) > 0)",
        "name": "sampling_batch_extent",
        "rationale": "Represents a fixed sampling setup cost plus batch-wide work when random sampling is enabled; the positive baseline avoids a feature supported only on sampling calls."
      },
      {
        "expression": "1 + int(len(self.engine_core.engine_core.scheduler.waiting) == 2 and len(self.engine_core.engine_core.scheduler.running) == 0)",
        "name": "admission_regime",
        "rationale": "Distinguishes the observed costly first mixed-sampling admission using the established workload-specific proxy, with a positive baseline."
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
        "active_requests": 42784511.24928922,
        "admission_regime": 15970015841.750338,
        "pending_tokens": 90124505.88059442,
        "sampling_batch_extent": 16617.29644541132
      },
      "constant": -15965066778.706158,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 82.06058311928064,
    "max_unexplained_share": 0.22236551037385652,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "active_requests",
      "pending_tokens",
      "sampling_batch_extent",
      "admission_regime"
    ],
    "raw_files": [
      "run.2321045.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 148020826.75,
        "state": {
          "active_requests": 1,
          "admission_regime": 1,
          "pending_tokens": 1,
          "sampling_batch_extent": 1
        },
        "unexplained_instructions_per_call": 10519432.75,
        "unexplained_share": 0.07106724763648842
      },
      {
        "calls": 1,
        "instructions_per_call": 176870482.0,
        "state": {
          "active_requests": 1,
          "admission_regime": 1,
          "pending_tokens": 1,
          "sampling_batch_extent": 3
        },
        "unexplained_instructions_per_call": 39329895.0,
        "unexplained_share": 0.22236551037385652
      },
      {
        "calls": 1,
        "instructions_per_call": 985611314.0,
        "state": {
          "active_requests": 1,
          "admission_regime": 1,
          "pending_tokens": 10,
          "sampling_batch_extent": 1
        },
        "unexplained_instructions_per_call": 36913625.0,
        "unexplained_share": 0.037452517514424556
      },
      {
        "calls": 2,
        "instructions_per_call": 294839932.5,
        "state": {
          "active_requests": 2,
          "admission_regime": 1,
          "pending_tokens": 2,
          "sampling_batch_extent": 1
        },
        "unexplained_instructions_per_call": 24267381.0,
        "unexplained_share": 0.08230696837511994
      },
      {
        "calls": 5,
        "instructions_per_call": 330798336.2,
        "state": {
          "active_requests": 2,
          "admission_regime": 1,
          "pending_tokens": 2,
          "sampling_batch_extent": 4
        },
        "unexplained_instructions_per_call": 60152150.80000006,
        "unexplained_share": 0.18183933900934796
      },
      {
        "calls": 1,
        "instructions_per_call": 18866015946.0,
        "state": {
          "active_requests": 2,
          "admission_regime": 2,
          "pending_tokens": 20,
          "sampling_batch_extent": 4
        },
        "unexplained_instructions_per_call": 1003018955.0,
        "unexplained_share": 0.05316538255193522
      },
      {
        "calls": 1,
        "instructions_per_call": 435701036.0,
        "state": {
          "active_requests": 3,
          "admission_regime": 1,
          "pending_tokens": 3,
          "sampling_batch_extent": 1
        },
        "unexplained_instructions_per_call": 32178122.0,
        "unexplained_share": 0.07385367337065502
      },
      {
        "calls": 2,
        "instructions_per_call": 494651582.0,
        "state": {
          "active_requests": 3,
          "admission_regime": 1,
          "pending_tokens": 3,
          "sampling_batch_extent": 5
        },
        "unexplained_instructions_per_call": 90843301.5,
        "unexplained_share": 0.1836510885757159
      },
      {
        "calls": 1,
        "instructions_per_call": 6336005620.0,
        "state": {
          "active_requests": 3,
          "admission_regime": 1,
          "pending_tokens": 66,
          "sampling_batch_extent": 5
        },
        "unexplained_instructions_per_call": 254246953.0,
        "unexplained_share": 0.04012732441357904
      },
      {
        "calls": 2,
        "instructions_per_call": 652906967.5,
        "state": {
          "active_requests": 4,
          "admission_regime": 1,
          "pending_tokens": 4,
          "sampling_batch_extent": 6
        },
        "unexplained_instructions_per_call": 116196404.0,
        "unexplained_share": 0.17796778068538532
      },
      {
        "calls": 1,
        "instructions_per_call": 8071595361.0,
        "state": {
          "active_requests": 4,
          "admission_regime": 1,
          "pending_tokens": 84,
          "sampling_batch_extent": 6
        },
        "unexplained_instructions_per_call": 324734434.0,
        "unexplained_share": 0.04023175338657812
      },
      {
        "calls": 2,
        "instructions_per_call": 813759808.5,
        "state": {
          "active_requests": 5,
          "admission_regime": 1,
          "pending_tokens": 5,
          "sampling_batch_extent": 7
        },
        "unexplained_instructions_per_call": 144076216.5,
        "unexplained_share": 0.17705005211006314
      },
      {
        "calls": 1,
        "instructions_per_call": 21685832616.0,
        "state": {
          "active_requests": 5,
          "admission_regime": 1,
          "pending_tokens": 230,
          "sampling_batch_extent": 7
        },
        "unexplained_instructions_per_call": 737987729.0,
        "unexplained_share": 0.03403086900410299
      },
      {
        "calls": 1,
        "instructions_per_call": 972582723.0,
        "state": {
          "active_requests": 6,
          "admission_regime": 1,
          "pending_tokens": 6,
          "sampling_batch_extent": 8
        },
        "unexplained_instructions_per_call": 169989624.0,
        "unexplained_share": 0.17478166122019423
      },
      {
        "calls": 1,
        "instructions_per_call": 25464143788.0,
        "state": {
          "active_requests": 6,
          "admission_regime": 1,
          "pending_tokens": 270,
          "sampling_batch_extent": 8
        },
        "unexplained_instructions_per_call": 868489273.0,
        "unexplained_share": 0.034106360701955996
      },
      {
        "calls": 1,
        "instructions_per_call": 30354183898.0,
        "state": {
          "active_requests": 7,
          "admission_regime": 1,
          "pending_tokens": 322,
          "sampling_batch_extent": 9
        },
        "unexplained_instructions_per_call": 1029210974.0,
        "unexplained_share": 0.03390672526260254
      },
      {
        "calls": 1,
        "instructions_per_call": 34690022413.0,
        "state": {
          "active_requests": 8,
          "admission_regime": 1,
          "pending_tokens": 368,
          "sampling_batch_extent": 10
        },
        "unexplained_instructions_per_call": 1176450255.0,
        "unexplained_share": 0.03391321691850877
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 22.236551037385652,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 22.236551037385652,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}