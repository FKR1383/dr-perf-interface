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
    "hypothesis": "First-output cost scales with total prompt length in addition to request count. Replacing accumulated generation length with prefill prompt tokens should explain the large increases for long-prompt batches.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(engine_core_outputs)",
        "name": "batch_size",
        "rationale": "Measures per-output processing and output construction."
      },
      {
        "expression": "sum((o.finish_reason is not None for o in engine_core_outputs))",
        "name": "finished_requests",
        "rationale": "Measures completion statistics and request cleanup."
      },
      {
        "expression": "sum((self.request_states[o.request_id].is_prefilling for o in engine_core_outputs if o.request_id in self.request_states))",
        "name": "prefilling_requests",
        "rationale": "Separates first-output processing from subsequent decoding steps."
      },
      {
        "expression": "sum((self.request_states[o.request_id].prompt_len for o in engine_core_outputs if o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling))",
        "name": "prefill_prompt_tokens",
        "rationale": "Measures prompt-dependent work during initial detokenization; the largest unexplained costs occur on first outputs with long prompts."
      }
    ]
  },
  "case_id": "vllm-047",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-047",
    "distinct_states": 18,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "batch_size": 11127.63659806388,
        "finished_requests": 19118.411743428245,
        "prefill_prompt_tokens": 1601.2929699449555,
        "prefilling_requests": 4418.1166849635265
      },
      "constant": 16761.701300446588,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 131.7080844109878,
    "max_unexplained_share": 0.7139358990430822,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "finished_requests",
      "prefilling_requests",
      "prefill_prompt_tokens"
    ],
    "raw_files": [
      "run.2327155.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 49909.8,
        "state": {
          "batch_size": 1,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 10177.8,
        "unexplained_share": 0.20392387867713352
      },
      {
        "calls": 1,
        "instructions_per_call": 239310.0,
        "state": {
          "batch_size": 1,
          "finished_requests": 1,
          "prefill_prompt_tokens": 10,
          "prefilling_requests": 1
        },
        "unexplained_instructions_per_call": 170852.0,
        "unexplained_share": 0.7139358990430822
      },
      {
        "calls": 1,
        "instructions_per_call": 35188.0,
        "state": {
          "batch_size": 2,
          "finished_requests": 0,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 5805.0,
        "unexplained_share": 0.16497101284528817
      },
      {
        "calls": 1,
        "instructions_per_call": 116316.0,
        "state": {
          "batch_size": 2,
          "finished_requests": 0,
          "prefill_prompt_tokens": 20,
          "prefilling_requests": 2
        },
        "unexplained_instructions_per_call": 43916.0,
        "unexplained_share": 0.3775576876783933
      },
      {
        "calls": 4,
        "instructions_per_call": 72450.25,
        "state": {
          "batch_size": 2,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 18606.75,
        "unexplained_share": 0.25682105996873716
      },
      {
        "calls": 2,
        "instructions_per_call": 95378.0,
        "state": {
          "batch_size": 2,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 19034.5,
        "unexplained_share": 0.19956908301704795
      },
      {
        "calls": 2,
        "instructions_per_call": 79364.5,
        "state": {
          "batch_size": 3,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 14302.0,
        "unexplained_share": 0.1802065155075632
      },
      {
        "calls": 1,
        "instructions_per_call": 270020.0,
        "state": {
          "batch_size": 3,
          "finished_requests": 1,
          "prefill_prompt_tokens": 66,
          "prefilling_requests": 3
        },
        "unexplained_instructions_per_call": 86056.0,
        "unexplained_share": 0.31870231834678914
      },
      {
        "calls": 1,
        "instructions_per_call": 111089.0,
        "state": {
          "batch_size": 3,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 20964.0,
        "unexplained_share": 0.18871355399724546
      },
      {
        "calls": 1,
        "instructions_per_call": 341108.0,
        "state": {
          "batch_size": 4,
          "finished_requests": 1,
          "prefill_prompt_tokens": 84,
          "prefilling_requests": 4
        },
        "unexplained_instructions_per_call": 108644.0,
        "unexplained_share": 0.3185032306483577
      },
      {
        "calls": 2,
        "instructions_per_call": 126148.0,
        "state": {
          "batch_size": 4,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 24279.5,
        "unexplained_share": 0.19246837048546153
      },
      {
        "calls": 1,
        "instructions_per_call": 108398.0,
        "state": {
          "batch_size": 5,
          "finished_requests": 1,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 19420.0,
        "unexplained_share": 0.17915459694828317
      },
      {
        "calls": 1,
        "instructions_per_call": 141239.0,
        "state": {
          "batch_size": 5,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 26373.0,
        "unexplained_share": 0.1867260459221603
      },
      {
        "calls": 1,
        "instructions_per_call": 754948.0,
        "state": {
          "batch_size": 5,
          "finished_requests": 2,
          "prefill_prompt_tokens": 230,
          "prefilling_requests": 5
        },
        "unexplained_instructions_per_call": 249454.0,
        "unexplained_share": 0.3304254067829837
      },
      {
        "calls": 1,
        "instructions_per_call": 834472.0,
        "state": {
          "batch_size": 6,
          "finished_requests": 1,
          "prefill_prompt_tokens": 270,
          "prefilling_requests": 6
        },
        "unexplained_instructions_per_call": 271460.0,
        "unexplained_share": 0.32530749983222923
      },
      {
        "calls": 1,
        "instructions_per_call": 155203.0,
        "state": {
          "batch_size": 6,
          "finished_requests": 2,
          "prefill_prompt_tokens": 0,
          "prefilling_requests": 0
        },
        "unexplained_instructions_per_call": 28068.0,
        "unexplained_share": 0.18084701970967057
      },
      {
        "calls": 1,
        "instructions_per_call": 1031643.0,
        "state": {
          "batch_size": 7,
          "finished_requests": 2,
          "prefill_prompt_tokens": 322,
          "prefilling_requests": 7
        },
        "unexplained_instructions_per_call": 345359.0,
        "unexplained_share": 0.3347659994785018
      },
      {
        "calls": 1,
        "instructions_per_call": 1177990.0,
        "state": {
          "batch_size": 8,
          "finished_requests": 2,
          "prefill_prompt_tokens": 368,
          "prefilling_requests": 8
        },
        "unexplained_instructions_per_call": 396220.0,
        "unexplained_share": 0.33635260061630406
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 71.39358990430821,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 71.39358990430821,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17"
  }
}