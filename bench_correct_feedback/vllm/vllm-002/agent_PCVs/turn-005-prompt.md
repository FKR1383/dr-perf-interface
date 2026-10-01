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

This is iteration 4. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Separating initialization from warm request processing should improve attribution. Warm costs depend on request count, prompt length, and special-token handling more directly than on option cardinality.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Separates the initial default-options call and its substantial initialization work."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params)",
        "name": "warm_request_count",
        "rationale": "Models per-request work in subsequent calls independently of initialization."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) * len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0])",
        "name": "prompt_character_work",
        "rationale": "Estimates text-processing work using constant-time access to a representative prompt."
      },
      {
        "expression": "len(params) if (prompts.gi_frame.f_locals.get('tokenization_kwargs') or {}).get('add_special_tokens', False) else 0",
        "name": "special_token_requests",
        "rationale": "Captures the tokenization branch that inserts special tokens, which alternates across subsequent batches."
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
        "default_tokenization": 53067867.6348388,
        "prompt_character_work": 1304.1984262716219,
        "special_token_requests": 1605.8793269844923,
        "warm_request_count": 671708.1013246123
      },
      "constant": 413207.39904625225,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 131.25232090521604,
    "max_unexplained_share": 0.29983967736753975,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "warm_request_count",
      "prompt_character_work",
      "special_token_requests"
    ],
    "raw_files": [
      "run.1782429.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 2304299.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 42,
          "special_token_requests": 0,
          "warm_request_count": 2
        },
        "unexplained_instructions_per_call": 530657.0,
        "unexplained_share": 0.23028999274833692
      },
      {
        "calls": 1,
        "instructions_per_call": 3687360.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 249,
          "special_token_requests": 3,
          "warm_request_count": 3
        },
        "unexplained_instructions_per_call": 938847.0,
        "unexplained_share": 0.25461224290549334
      },
      {
        "calls": 1,
        "instructions_per_call": 4571287.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 332,
          "special_token_requests": 0,
          "warm_request_count": 4
        },
        "unexplained_instructions_per_call": 1057092.0,
        "unexplained_share": 0.23124603640068978
      },
      {
        "calls": 1,
        "instructions_per_call": 6904203.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 780,
          "special_token_requests": 5,
          "warm_request_count": 5
        },
        "unexplained_instructions_per_call": 2070154.0,
        "unexplained_share": 0.29983967736753975
      },
      {
        "calls": 1,
        "instructions_per_call": 7949995.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 936,
          "special_token_requests": 0,
          "warm_request_count": 6
        },
        "unexplained_instructions_per_call": 2303713.0,
        "unexplained_share": 0.2897754023744669
      },
      {
        "calls": 1,
        "instructions_per_call": 9262729.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 1092,
          "special_token_requests": 7,
          "warm_request_count": 7
        },
        "unexplained_instructions_per_call": 2687288.0,
        "unexplained_share": 0.2901183873564691
      },
      {
        "calls": 1,
        "instructions_per_call": 10531724.0,
        "state": {
          "default_tokenization": 0,
          "prompt_character_work": 1248,
          "special_token_requests": 0,
          "warm_request_count": 8
        },
        "unexplained_instructions_per_call": 3060753.0,
        "unexplained_share": 0.29062221911626246
      },
      {
        "calls": 1,
        "instructions_per_call": 59683411.0,
        "state": {
          "default_tokenization": 1,
          "prompt_character_work": 0,
          "special_token_requests": 0,
          "warm_request_count": 0
        },
        "unexplained_instructions_per_call": 6236761.0,
        "unexplained_share": 0.10449739543204058
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 29.983967736753975,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 29.983967736753975,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}