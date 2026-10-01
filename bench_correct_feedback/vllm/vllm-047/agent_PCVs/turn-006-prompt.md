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
    "hypothesis": "Prompt length alone omits fixed first-output initialization costs. Adding a small per-request offset to the prefill work measure should better explain both short and long prompts while retaining completion and exceptional-regime features.",
    "iteration": 4,
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
        "expression": "sum((self.request_states[o.request_id].prompt_len + 6 for o in engine_core_outputs if o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling))",
        "name": "prefill_work",
        "rationale": "Combines prompt-length-dependent work with fixed initialization work per prefilling request."
      },
      {
        "expression": "int(len(engine_core_outputs) > 0 and sum((o.finish_reason is not None and o.request_id in self.request_states and self.request_states[o.request_id].is_prefilling for o in engine_core_outputs)) == len(engine_core_outputs))",
        "name": "entire_batch_finishes_on_first_output",
        "rationale": "Separates the exceptional regime where every request finishes on its first output."
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
        "batch_size": 9607.994850257235,
        "entire_batch_finishes_on_first_output": 133776.44992956397,
        "finished_requests": 25141.491389837334,
        "prefill_work": 438.58278052638144
      },
      "constant": 14361.773451763873,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 128.33877306897193,
    "max_unexplained_share": 0.7221743023745003,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "finished_requests",
      "prefill_work",
      "entire_batch_finishes_on_first_output"
    ],
    "raw_files": [
      "run.2329125.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 50458.6,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 8169.999999999998,
        "unexplained_share": 0.16191491638689934
      },
      {
        "calls": 1,
        "instructions_per_call": 238848.0,
        "state": {
          "batch_size": 1,
          "entire_batch_finishes_on_first_output": 1,
          "finished_requests": 1,
          "prefill_work": 16
        },
        "unexplained_instructions_per_call": 53355.0,
        "unexplained_share": 0.2233847467845659
      },
      {
        "calls": 1,
        "instructions_per_call": 35536.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 9126.0,
        "unexplained_share": 0.25680999549752365
      },
      {
        "calls": 1,
        "instructions_per_call": 114226.0,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 0,
          "prefill_work": 32
        },
        "unexplained_instructions_per_call": 67797.0,
        "unexplained_share": 0.5935338714478315
      },
      {
        "calls": 4,
        "instructions_per_call": 73133.25,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 17360.25,
        "unexplained_share": 0.2373783470582806
      },
      {
        "calls": 2,
        "instructions_per_call": 96019.5,
        "state": {
          "batch_size": 2,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 15012.5,
        "unexplained_share": 0.15634845005441603
      },
      {
        "calls": 2,
        "instructions_per_call": 80161.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 15890.0,
        "unexplained_share": 0.19822607003405646
      },
      {
        "calls": 1,
        "instructions_per_call": 267589.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 84
        },
        "unexplained_instructions_per_call": 163805.0,
        "unexplained_share": 0.6121514710993352
      },
      {
        "calls": 1,
        "instructions_per_call": 111552.0,
        "state": {
          "batch_size": 3,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 18625.0,
        "unexplained_share": 0.16696249282845668
      },
      {
        "calls": 1,
        "instructions_per_call": 340060.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 108
        },
        "unexplained_instructions_per_call": 214251.0,
        "unexplained_share": 0.6300388166794095
      },
      {
        "calls": 2,
        "instructions_per_call": 125793.0,
        "state": {
          "batch_size": 4,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 22871.5,
        "unexplained_share": 0.18181854316217913
      },
      {
        "calls": 1,
        "instructions_per_call": 109954.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 24930.0,
        "unexplained_share": 0.22673117849282426
      },
      {
        "calls": 1,
        "instructions_per_call": 140794.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 26812.0,
        "unexplained_share": 0.19043425145957923
      },
      {
        "calls": 1,
        "instructions_per_call": 751884.0,
        "state": {
          "batch_size": 5,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 260
        },
        "unexplained_instructions_per_call": 519224.0,
        "unexplained_share": 0.6905639699740918
      },
      {
        "calls": 1,
        "instructions_per_call": 850958.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 1,
          "prefill_work": 306
        },
        "unexplained_instructions_per_call": 614540.0,
        "unexplained_share": 0.7221743023745003
      },
      {
        "calls": 1,
        "instructions_per_call": 155315.0,
        "state": {
          "batch_size": 6,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 0
        },
        "unexplained_instructions_per_call": 30931.0,
        "unexplained_share": 0.19915011428387472
      },
      {
        "calls": 1,
        "instructions_per_call": 1023032.0,
        "state": {
          "batch_size": 7,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 364
        },
        "unexplained_instructions_per_call": 723392.0,
        "unexplained_share": 0.7071059360802008
      },
      {
        "calls": 1,
        "instructions_per_call": 1173883.0,
        "state": {
          "batch_size": 8,
          "entire_batch_finishes_on_first_output": 0,
          "finished_requests": 2,
          "prefill_work": 416
        },
        "unexplained_instructions_per_call": 838876.0,
        "unexplained_share": 0.7146163629595113
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 72.21743023745003,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 72.21743023745003,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ab8cc6ad2c39a430fbeaabf84126c47218f5526ef51e2f197b1fc22c9ef3de17"
  }
}