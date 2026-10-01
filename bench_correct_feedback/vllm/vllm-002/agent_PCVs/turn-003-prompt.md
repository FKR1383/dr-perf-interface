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

This is iteration 2. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Instruction count is primarily proportional to request count, with additional per-request work depending on the number of tokenization options.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Each request incurs rendering, validation, engine insertion, and result-list overhead."
      },
      {
        "expression": "len(params) * len(prompts.gi_frame.f_locals.get('tokenization_kwargs') or {})",
        "name": "tokenization_option_work",
        "rationale": "The generator captures tokenization options that are processed separately for every prompt."
      }
    ]
  },
  "case_id": "vllm-002",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 8,
    "case": "vllm-002",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "request_count": 14991.92857142879,
        "tokenization_option_work": 6315.547619047584
      },
      "constant": 225272.32142857235,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 141.47031461633742,
    "max_unexplained_share": 0.9952034852750626,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "request_count",
      "tokenization_option_work"
    ],
    "raw_files": [
      "run.1780152.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 59697096.0,
        "state": {
          "request_count": 1,
          "tokenization_option_work": 0
        },
        "unexplained_instructions_per_call": 59410758.0,
        "unexplained_share": 0.9952034852750626
      },
      {
        "calls": 1,
        "instructions_per_call": 2301538.0,
        "state": {
          "request_count": 2,
          "tokenization_option_work": 2
        },
        "unexplained_instructions_per_call": 2102193.0,
        "unexplained_share": 0.9133861791549824
      },
      {
        "calls": 1,
        "instructions_per_call": 3682422.0,
        "state": {
          "request_count": 3,
          "tokenization_option_work": 6
        },
        "unexplained_instructions_per_call": 3397456.0,
        "unexplained_share": 0.9226145183794796
      },
      {
        "calls": 1,
        "instructions_per_call": 4554830.0,
        "state": {
          "request_count": 4,
          "tokenization_option_work": 12
        },
        "unexplained_instructions_per_call": 4202815.0,
        "unexplained_share": 0.9227161057602589
      },
      {
        "calls": 1,
        "instructions_per_call": 6900230.0,
        "state": {
          "request_count": 5,
          "tokenization_option_work": 20
        },
        "unexplained_instructions_per_call": 6440598.0,
        "unexplained_share": 0.9333888870370988
      },
      {
        "calls": 1,
        "instructions_per_call": 7922283.0,
        "state": {
          "request_count": 6,
          "tokenization_option_work": 30
        },
        "unexplained_instructions_per_call": 7398897.0,
        "unexplained_share": 0.9339349528412454
      },
      {
        "calls": 1,
        "instructions_per_call": 9247380.0,
        "state": {
          "request_count": 7,
          "tokenization_option_work": 42
        },
        "unexplained_instructions_per_call": 8638467.0,
        "unexplained_share": 0.9341529168261713
      },
      {
        "calls": 1,
        "instructions_per_call": 10519498.0,
        "state": {
          "request_count": 8,
          "tokenization_option_work": 56
        },
        "unexplained_instructions_per_call": 9831193.0,
        "unexplained_share": 0.9345686457661763
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 99.52034852750626,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 99.52034852750626,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}