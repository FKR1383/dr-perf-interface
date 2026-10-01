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
    "hypothesis": "The previous features isolated the exceptional states but still underpredicted their costs. Scaling the sparse regime indicators tests whether fitting regularization contributes to the remaining irregularity.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0",
        "name": "prompt_tokens",
        "rationale": "Captures token-dependent admission work."
      },
      {
        "expression": "len(prompt_text or '') if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt', '') or '') if isinstance(prompt, dict) else len(prompt) if isinstance(prompt, str) else 0",
        "name": "prompt_characters",
        "rationale": "Captures text-dependent initialization work."
      },
      {
        "expression": "1024 * int((len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0) == 10)",
        "name": "ten_token_regime",
        "rationale": "Retains the observed initialization proxy, scaled to reduce possible fitting shrinkage of a sparse indicator."
      },
      {
        "expression": "1024 * int((len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0) == 9)",
        "name": "nine_token_regime",
        "rationale": "Retains the second exceptional short-prompt regime with the same numerical scaling."
      }
    ]
  },
  "case_id": "vllm-045",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-045",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "nine_token_regime": 42.584300700226684,
        "prompt_characters": 276.0422533863925,
        "prompt_tokens": -504.55854975501984,
        "ten_token_regime": 44770.59768410169
      },
      "constant": 482256.38838207134,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 96.84633860224858,
    "max_unexplained_share": 0.14035040078207614,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "prompt_characters",
      "ten_token_regime",
      "nine_token_regime"
    ],
    "raw_files": [
      "run.2309616.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 626026.0,
        "state": {
          "nine_token_regime": 1024,
          "prompt_characters": 21,
          "prompt_tokens": 9,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 87863.0,
        "unexplained_share": 0.14035040078207614
      },
      {
        "calls": 1,
        "instructions_per_call": 48690916.0,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 21,
          "prompt_tokens": 10,
          "ten_token_regime": 1024
        },
        "unexplained_instructions_per_call": 2361802.0,
        "unexplained_share": 0.048506008800491655
      },
      {
        "calls": 1,
        "instructions_per_call": 534394.0,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 33,
          "prompt_tokens": 11,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 50839.0,
        "unexplained_share": 0.09513392740187951
      },
      {
        "calls": 4,
        "instructions_per_call": 548592.25,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 83,
          "prompt_tokens": 21,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 56848.5,
        "unexplained_share": 0.10362614491910886
      },
      {
        "calls": 3,
        "instructions_per_call": 559500.3333333334,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 83,
          "prompt_tokens": 22,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 62872.33333333332,
        "unexplained_share": 0.11237228932243708
      },
      {
        "calls": 10,
        "instructions_per_call": 549344.2,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 156,
          "prompt_tokens": 45,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 50842.8,
        "unexplained_share": 0.09255180995812827
      },
      {
        "calls": 12,
        "instructions_per_call": 553356.0833333334,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 156,
          "prompt_tokens": 46,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 53003.66666666666,
        "unexplained_share": 0.09578582085405221
      },
      {
        "calls": 4,
        "instructions_per_call": 549474.0,
        "state": {
          "nine_token_regime": 0,
          "prompt_characters": 162,
          "prompt_tokens": 47,
          "ten_token_regime": 0
        },
        "unexplained_instructions_per_call": 49873.75,
        "unexplained_share": 0.09076635109213539
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 14.035040078207613,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 14.035040078207613,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}