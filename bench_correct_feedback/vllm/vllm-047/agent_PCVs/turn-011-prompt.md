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
    "hypothesis": "The dominant initialization loops may process prompt tokens plus the first generated tokens specifically on initial outputs. This differs from both prompt-only counts and counting incoming tokens on every decoding call.",
    "iteration": 9,
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
        "expression": "sum((self.request_states[o.request_id].prompt_len + len(o.new_token_ids) for o in engine_core_outputs if o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling))",
        "name": "initial_decode_tokens",
        "rationale": "Measures the complete token sequence available for initial decoding, including newly generated tokens."
      },
      {
        "expression": "int(len(engine_core_outputs) > 0 and sum((o.finish_reason is not None and o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling for o in engine_core_outputs)) == len(engine_core_outputs))",
        "name": "entire_batch_finishes_on_first_output",
        "rationale": "Separates the exceptional first-output completion regime."
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
        "batch_size": 11202.88477970194,
        "entire_batch_finishes_on_first_output": 133626.6717800769,
        "finished_requests": 25028.003376722107,
        "initial_decode_tokens": 1252.6049569298211
      },
      "constant": 17073.757107546087,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 100.05440123192966,
    "max_unexplained_share": 0.45814680086066667,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "finished_requests",
      "initial_decode_tokens",
      "entire_batch_finishes_on_first_output"
    ],
    "raw_files": [
      "run.2334122.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 49862.6,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 5602.5999999999985,
        "unexplained_share": 0.11236076738878435
      },
      {
        "calls": 1,
        "instructions_per_call": 239790.0,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 1,
          "finished_requests": 1,
          "initial_decode_tokens": 11
        },
        "unexplained_instructions_per_call": 45059.0,
        "unexplained_share": 0.18791025480628884
      },
      {
        "calls": 1,
        "instructions_per_call": 35133.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 4524.0,
        "unexplained_share": 0.12876782512168047
      },
      {
        "calls": 1,
        "instructions_per_call": 113576.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "initial_decode_tokens": 22
        },
        "unexplained_instructions_per_call": 46477.0,
        "unexplained_share": 0.4092149749947172
      },
      {
        "calls": 4,
        "instructions_per_call": 72114.75,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 12618.75,
        "unexplained_share": 0.17498153983755058
      },
      {
        "calls": 2,
        "instructions_per_call": 95608.5,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 10347.0,
        "unexplained_share": 0.10822259527134094
      },
      {
        "calls": 2,
        "instructions_per_call": 79931.5,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 9064.0,
        "unexplained_share": 0.11339709626367578
      },
      {
        "calls": 1,
        "instructions_per_call": 267930.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 69
        },
        "unexplained_instructions_per_call": 107564.0,
        "unexplained_share": 0.401463068711977
      },
      {
        "calls": 1,
        "instructions_per_call": 111149.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 11688.0,
        "unexplained_share": 0.10515614175566132
      },
      {
        "calls": 1,
        "instructions_per_call": 342367.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 88
        },
        "unexplained_instructions_per_call": 140866.0,
        "unexplained_share": 0.4114473649621605
      },
      {
        "calls": 2,
        "instructions_per_call": 125470.5,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 13875.5,
        "unexplained_share": 0.11058774771759099
      },
      {
        "calls": 1,
        "instructions_per_call": 108447.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 13233.0,
        "unexplained_share": 0.12202273921823563
      },
      {
        "calls": 1,
        "instructions_per_call": 141067.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 16134.0,
        "unexplained_share": 0.11437118532328609
      },
      {
        "calls": 1,
        "instructions_per_call": 751802.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 235
        },
        "unexplained_instructions_per_call": 330754.0,
        "unexplained_share": 0.439948284255695
      },
      {
        "calls": 1,
        "instructions_per_call": 853292.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "initial_decode_tokens": 276
        },
        "unexplained_instructions_per_call": 390933.0,
        "unexplained_share": 0.45814680086066667
      },
      {
        "calls": 1,
        "instructions_per_call": 155402.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 0
        },
        "unexplained_instructions_per_call": 17768.0,
        "unexplained_share": 0.11433572283496996
      },
      {
        "calls": 1,
        "instructions_per_call": 1026250.0,
        "state": {
          "batch_size": 7,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 329
        },
        "unexplained_instructions_per_call": 459628.0,
        "unexplained_share": 0.4478713763702801
      },
      {
        "calls": 1,
        "instructions_per_call": 1180258.0,
        "state": {
          "batch_size": 8,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "initial_decode_tokens": 376
        },
        "unexplained_instructions_per_call": 537527.0,
        "unexplained_share": 0.45543177847555366
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 45.814680086066666,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 45.814680086066666,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17"
  }
}