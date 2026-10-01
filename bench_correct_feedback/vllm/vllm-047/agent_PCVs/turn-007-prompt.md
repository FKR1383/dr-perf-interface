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
    "hypothesis": "The combined token-count feature worsened attribution. Initial decoding may instead scale with prompt characters processed by the tokenizer; this candidate tests that alternative while preserving the other workload dimensions.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "len(engine_core_outputs)",
        "name": "batch_size",
        "rationale": "Captures per-request processing and output construction."
      },
      {
        "expression": "sum((o.finish_reason is not None for o in engine_core_outputs))",
        "name": "finished_requests",
        "rationale": "Captures completion statistics and cleanup."
      },
      {
        "expression": "sum((len(self.request_states[o.request_id].prompt or '') for o in engine_core_outputs if o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling))",
        "name": "prefill_prompt_characters",
        "rationale": "Tests whether initial tokenizer work follows text length more closely than token count."
      },
      {
        "expression": "int(len(engine_core_outputs) > 0 and sum((o.finish_reason is not None and o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling for o in engine_core_outputs)) == len(engine_core_outputs))",
        "name": "entire_batch_finishes_on_first_output",
        "rationale": "Retains separation of the exceptional first-output completion regime."
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
        "batch_size": 9059.294006033888,
        "entire_batch_finishes_on_first_output": 134361.14138430267,
        "finished_requests": 25038.647051051954,
        "prefill_prompt_characters": 252.1551507596961
      },
      "constant": 16111.422165344004,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 138.77361390274018,
    "max_unexplained_share": 0.6087374445223078,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "finished_requests",
      "prefill_prompt_characters",
      "entire_batch_finishes_on_first_output"
    ],
    "raw_files": [
      "run.2330253.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 50419.4,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 7965.799999999998,
        "unexplained_share": 0.1579907733927813
      },
      {
        "calls": 1,
        "instructions_per_call": 240082.0,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 1,
          "finished_requests": 1,
          "prefill_prompt_characters": 21
        },
        "unexplained_instructions_per_call": 52726.0,
        "unexplained_share": 0.21961663098441367
      },
      {
        "calls": 1,
        "instructions_per_call": 36731.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 9782.0,
        "unexplained_share": 0.26631455718602814
      },
      {
        "calls": 1,
        "instructions_per_call": 115341.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_prompt_characters": 54
        },
        "unexplained_instructions_per_call": 64289.0,
        "unexplained_share": 0.5573820237383064
      },
      {
        "calls": 4,
        "instructions_per_call": 72741.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 17572.25,
        "unexplained_share": 0.24157284062633178
      },
      {
        "calls": 2,
        "instructions_per_call": 96059.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 15413.5,
        "unexplained_share": 0.16045867643843886
      },
      {
        "calls": 2,
        "instructions_per_call": 80390.5,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 16871.0,
        "unexplained_share": 0.20986310571522754
      },
      {
        "calls": 1,
        "instructions_per_call": 269882.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 249
        },
        "unexplained_instructions_per_call": 137880.0,
        "unexplained_share": 0.5108899444942605
      },
      {
        "calls": 1,
        "instructions_per_call": 112631.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 20433.0,
        "unexplained_share": 0.18141541849046888
      },
      {
        "calls": 1,
        "instructions_per_call": 340966.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 332
        },
        "unexplained_instructions_per_call": 178170.0,
        "unexplained_share": 0.5225447698597514
      },
      {
        "calls": 2,
        "instructions_per_call": 125691.5,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 24096.5,
        "unexplained_share": 0.19171145224617417
      },
      {
        "calls": 1,
        "instructions_per_call": 109229.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 25585.0,
        "unexplained_share": 0.2342326671488341
      },
      {
        "calls": 1,
        "instructions_per_call": 141152.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 28869.0,
        "unexplained_share": 0.20452420086148265
      },
      {
        "calls": 1,
        "instructions_per_call": 753735.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 780
        },
        "unexplained_instructions_per_call": 440257.0,
        "unexplained_share": 0.5841005127796904
      },
      {
        "calls": 1,
        "instructions_per_call": 856200.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_prompt_characters": 936
        },
        "unexplained_instructions_per_call": 521201.0,
        "unexplained_share": 0.6087374445223078
      },
      {
        "calls": 1,
        "instructions_per_call": 155335.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 33056.0,
        "unexplained_share": 0.2128045836418064
      },
      {
        "calls": 1,
        "instructions_per_call": 1026031.0,
        "state": {
          "batch_size": 7,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 1092
        },
        "unexplained_instructions_per_call": 611744.0,
        "unexplained_share": 0.5962237008433469
      },
      {
        "calls": 1,
        "instructions_per_call": 1182852.0,
        "state": {
          "batch_size": 8,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_prompt_characters": 1272
        },
        "unexplained_instructions_per_call": 714965.0,
        "unexplained_share": 0.6044416376689561
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 60.87374445223078,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 60.87374445223078,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17"
  }
}