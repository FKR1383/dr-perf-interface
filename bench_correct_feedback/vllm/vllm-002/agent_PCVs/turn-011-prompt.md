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
    "hypothesis": "Character volume and token volume drive distinct execution paths. Retaining both while incorporating special tokens into the token estimate should improve on the earlier character-and-word model.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Separates initialization work in the initial default-options call."
      },
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Tracks common per-request processing."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else sum((len(p['prompt'] if 'prompt' in p else p) for p in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable))",
        "name": "total_prompt_characters",
        "rationale": "Tracks character-dependent rendering and tokenization work independently of token volume."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else sum((t.count(' ') + 1 + t.count('.') + t.count(',') + t.count('-') + 2 * t.count('epsilon') + t.count('zeta') + t.count(' eta') + 2 * t.count('Distinguish') + t.count('Explain') + (1 if prompts.gi_frame.f_locals['tokenization_kwargs'].get('add_special_tokens', False) else 0) for p in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable for t in [p['prompt'] if 'prompt' in p else p]))",
        "name": "estimated_prompt_tokens",
        "rationale": "Estimates token-dependent processing, including punctuation, likely subword splits, and explicitly requested special tokens."
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
        "default_tokenization": 52210324.799792685,
        "estimated_prompt_tokens": 2154.2826323400595,
        "request_count": 644192.4118901133,
        "total_prompt_characters": 911.9686695839255
      },
      "constant": 432226.22558128956,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 97.63446982996538,
    "max_unexplained_share": 0.29876403217035485,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "request_count",
      "total_prompt_characters",
      "estimated_prompt_tokens"
    ],
    "raw_files": [
      "run.1788593.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 2307094.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 18,
          "request_count": 2,
          "total_prompt_characters": 54
        },
        "unexplained_instructions_per_call": 542710.0,
        "unexplained_share": 0.23523532201115344
      },
      {
        "calls": 1,
        "instructions_per_call": 3678520.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 66,
          "request_count": 3,
          "total_prompt_characters": 249
        },
        "unexplained_instructions_per_call": 957438.0,
        "unexplained_share": 0.26027804660570014
      },
      {
        "calls": 1,
        "instructions_per_call": 4560524.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 84,
          "request_count": 4,
          "total_prompt_characters": 332
        },
        "unexplained_instructions_per_call": 1064519.0,
        "unexplained_share": 0.23342032626075424
      },
      {
        "calls": 1,
        "instructions_per_call": 6905115.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 210,
          "request_count": 5,
          "total_prompt_characters": 780
        },
        "unexplained_instructions_per_call": 2063000.0,
        "unexplained_share": 0.29876403217035485
      },
      {
        "calls": 1,
        "instructions_per_call": 7943394.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 246,
          "request_count": 6,
          "total_prompt_characters": 936
        },
        "unexplained_instructions_per_call": 2267439.0,
        "unexplained_share": 0.2854496453279291
      },
      {
        "calls": 1,
        "instructions_per_call": 9252741.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 294,
          "request_count": 7,
          "total_prompt_characters": 1092
        },
        "unexplained_instructions_per_call": 2659405.0,
        "unexplained_share": 0.2874180742765846
      },
      {
        "calls": 1,
        "instructions_per_call": 10531224.0,
        "state": {
          "default_tokenization": 0,
          "estimated_prompt_tokens": 332,
          "request_count": 8,
          "total_prompt_characters": 1272
        },
        "unexplained_instructions_per_call": 3023597.0,
        "unexplained_share": 0.2871078423552666
      },
      {
        "calls": 1,
        "instructions_per_call": 59677354.0,
        "state": {
          "default_tokenization": 1,
          "estimated_prompt_tokens": 0,
          "request_count": 1,
          "total_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 6426011.0,
        "unexplained_share": 0.10767922116654166
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 29.876403217035485,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 29.876403217035485,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}