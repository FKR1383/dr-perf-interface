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
    "hypothesis": "A shared request-count feature should explain common execution paths more directly than disjoint counts, while medium- and long-prompt features explain their additional work.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Captures the initial default-options call and its additional initialization work."
      },
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Explains common per-request work across every prompt-length regime."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) if 64 <= len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]) < 128 else 0",
        "name": "medium_prompt_requests",
        "rationale": "Captures additional processing associated with medium-length prompts."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) if len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]) >= 128 else 0",
        "name": "long_prompt_requests",
        "rationale": "Captures additional processing associated with long prompts."
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
        "default_tokenization": 54352262.5830859,
        "long_prompt_requests": 324246.7922848643,
        "medium_prompt_requests": 113297.15727002789,
        "request_count": 760821.9065281916
      },
      "constant": 588621.5102002799,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 145.37000281410292,
    "max_unexplained_share": 0.14141594616079775,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "request_count",
      "medium_prompt_requests",
      "long_prompt_requests"
    ],
    "raw_files": [
      "run.1784362.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 2317122.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 0,
          "request_count": 2
        },
        "unexplained_instructions_per_call": 327678.0,
        "unexplained_share": 0.14141594616079775
      },
      {
        "calls": 1,
        "instructions_per_call": 3674169.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 3,
          "request_count": 3
        },
        "unexplained_instructions_per_call": 486290.0,
        "unexplained_share": 0.13235373767510422
      },
      {
        "calls": 1,
        "instructions_per_call": 4561976.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 4,
          "request_count": 4
        },
        "unexplained_instructions_per_call": 480151.0,
        "unexplained_share": 0.1052506633090573
      },
      {
        "calls": 1,
        "instructions_per_call": 6895801.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 5,
          "medium_prompt_requests": 0,
          "request_count": 5
        },
        "unexplained_instructions_per_call": 833080.0,
        "unexplained_share": 0.12080975074541739
      },
      {
        "calls": 1,
        "instructions_per_call": 7934494.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 6,
          "medium_prompt_requests": 0,
          "request_count": 6
        },
        "unexplained_instructions_per_call": 841561.0,
        "unexplained_share": 0.10606360027495138
      },
      {
        "calls": 1,
        "instructions_per_call": 9258540.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 7,
          "medium_prompt_requests": 0,
          "request_count": 7
        },
        "unexplained_instructions_per_call": 980348.0,
        "unexplained_share": 0.10588580920965941
      },
      {
        "calls": 1,
        "instructions_per_call": 10506494.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 8,
          "medium_prompt_requests": 0,
          "request_count": 8
        },
        "unexplained_instructions_per_call": 1090809.0,
        "unexplained_share": 0.103822359771014
      },
      {
        "calls": 1,
        "instructions_per_call": 59684046.0,
        "state": {
          "default_tokenization": 1,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 0,
          "request_count": 1
        },
        "unexplained_instructions_per_call": 4118405.0,
        "unexplained_share": 0.06900344859328068
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 14.141594616079775,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 14.141594616079775,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}