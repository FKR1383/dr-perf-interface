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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Token-processing volume may explain the text-dependent execution paths better than character counts. A lexical token estimate leaves a separate feature available for the alternating special-token branch.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Separates the initial call and its initialization work."
      },
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Tracks common work per request."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else sum((t.count(' ') + 1 + t.count('.') + t.count(',') + t.count('-') + 2 * t.count('epsilon') + t.count('zeta') + t.count(' eta') + 2 * t.count('Distinguish') + t.count('Explain') for p in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable for t in [p['prompt'] if 'prompt' in p else p]))",
        "name": "estimated_prompt_tokens",
        "rationale": "Estimates token-processing volume using word boundaries, punctuation, and likely subword splits in the supplied texts, without running the tokenizer."
      },
      {
        "expression": "len(params) if (prompts.gi_frame.f_locals.get('tokenization_kwargs') or {}).get('add_special_tokens', False) else 0",
        "name": "special_token_requests",
        "rationale": "Captures additional processing when tokenization inserts special tokens."
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
        "default_tokenization": 52187092.90344616,
        "estimated_prompt_tokens": 5720.05317188656,
        "request_count": 669570.233383974,
        "special_token_requests": 1387.285291318114
      },
      "constant": 389747.21851012576,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 127.55342859309167,
    "max_unexplained_share": 0.28183708666100576,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "request_count",
      "estimated_prompt_tokens",
      "special_token_requests"
    ],
    "raw_files": [
      "run.1787403.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 2290861.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 18,
          "request_count": 2,
          "special_token_requests": 0
        },
        "unexplained_instructions_per_call": 526426.0,
        "unexplained_share": 0.22979395083333298
      },
      {
        "calls": 1,
        "instructions_per_call": 3683690.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 63,
          "request_count": 3,
          "special_token_requests": 3
        },
        "unexplained_instructions_per_call": 930602.0,
        "unexplained_share": 0.2526276641085433
      },
      {
        "calls": 1,
        "instructions_per_call": 4565044.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 84,
          "request_count": 4,
          "special_token_requests": 0
        },
        "unexplained_instructions_per_call": 1030182.0,
        "unexplained_share": 0.22566748535172937
      },
      {
        "calls": 1,
        "instructions_per_call": 6903474.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 205,
          "request_count": 5,
          "special_token_requests": 5
        },
        "unexplained_instructions_per_call": 1945655.0,
        "unexplained_share": 0.28183708666100576
      },
      {
        "calls": 1,
        "instructions_per_call": 7957070.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 246,
          "request_count": 6,
          "special_token_requests": 0
        },
        "unexplained_instructions_per_call": 2142427.0,
        "unexplained_share": 0.26924822830514245
      },
      {
        "calls": 1,
        "instructions_per_call": 9274018.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 287,
          "request_count": 7,
          "special_token_requests": 7
        },
        "unexplained_instructions_per_call": 2512479.0,
        "unexplained_share": 0.27091590721518977
      },
      {
        "calls": 1,
        "instructions_per_call": 10524514.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 332,
          "request_count": 8,
          "special_token_requests": 0
        },
        "unexplained_instructions_per_call": 2830635.0,
        "unexplained_share": 0.26895636226052816
      },
      {
        "calls": 1,
        "instructions_per_call": 59662152.0,
        "state": {
          "default_tokenization": 1,
          "estimated_prompt_tokens": 0,
          "request_count": 1,
          "special_token_requests": 0
        },
        "unexplained_instructions_per_call": 6447743.0,
        "unexplained_share": 0.10807090900777432
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 28.183708666100575,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 28.183708666100575,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}