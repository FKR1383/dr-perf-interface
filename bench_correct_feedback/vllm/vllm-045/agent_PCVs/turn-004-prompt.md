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
    "hypothesis": "The measurements suggest exceptional initialization costs in two distinct short-prompt states, followed by relatively uniform admission costs. Explicit indicators isolate these exceptions while prompt sizes model steady-state variation.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0",
        "name": "prompt_tokens",
        "rationale": "Models token-dependent admission work across the observed prompt sizes."
      },
      {
        "expression": "len(prompt_text or '') if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt', '') or '') if isinstance(prompt, dict) else len(prompt) if isinstance(prompt, str) else 0",
        "name": "prompt_characters",
        "rationale": "Models text-dependent request and detokenizer setup."
      },
      {
        "expression": "int((len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0) == 10)",
        "name": "ten_token_prompt",
        "rationale": "Separates the observed ten-token state with exceptionally high cost; this is a workload-specific proxy for initialization, not an assumed general token-length effect."
      },
      {
        "expression": "int((len(prompt.prompt_token_ids or []) if isinstance(prompt, EngineCoreRequest) else len(prompt.get('prompt_token_ids', [])) if isinstance(prompt, dict) else 0) == 9)",
        "name": "nine_token_prompt",
        "rationale": "Separates the other short-prompt state, whose cost exceeds the steady-state calls."
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
        "nine_token_prompt": 43747.41534276446,
        "prompt_characters": 360.1863338849021,
        "prompt_tokens": -795.9957314927116,
        "ten_token_prompt": 45864171.353811644
      },
      "constant": 484804.57726619585,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 125.14381436211988,
    "max_unexplained_share": 0.1383110693878333,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_tokens",
      "prompt_characters",
      "ten_token_prompt",
      "nine_token_prompt"
    ],
    "raw_files": [
      "run.2308786.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 626349.0,
        "state": {
          "nine_token_prompt": 1,
          "prompt_characters": 21,
          "prompt_tokens": 9,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 86631.0,
        "unexplained_share": 0.1383110693878333
      },
      {
        "calls": 1,
        "instructions_per_call": 48687937.0,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 21,
          "prompt_tokens": 10,
          "ten_token_prompt": 1
        },
        "unexplained_instructions_per_call": 2337777.0,
        "unexplained_share": 0.04801552795305334
      },
      {
        "calls": 1,
        "instructions_per_call": 533205.0,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 33,
          "prompt_tokens": 11,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 47510.0,
        "unexplained_share": 0.08910269033486183
      },
      {
        "calls": 4,
        "instructions_per_call": 547905.75,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 83,
          "prompt_tokens": 21,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 52733.75,
        "unexplained_share": 0.09624602406527034
      },
      {
        "calls": 3,
        "instructions_per_call": 559512.6666666666,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 83,
          "prompt_tokens": 22,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 59337.66666666666,
        "unexplained_share": 0.1060524098948013
      },
      {
        "calls": 10,
        "instructions_per_call": 549595.5,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 156,
          "prompt_tokens": 45,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 48638.90000000001,
        "unexplained_share": 0.0884994509598423
      },
      {
        "calls": 12,
        "instructions_per_call": 553912.1666666666,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 156,
          "prompt_tokens": 46,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 50888.49999999999,
        "unexplained_share": 0.09187106379380845
      },
      {
        "calls": 4,
        "instructions_per_call": 547993.75,
        "state": {
          "nine_token_prompt": 0,
          "prompt_characters": 162,
          "prompt_tokens": 47,
          "ten_token_prompt": 0
        },
        "unexplained_instructions_per_call": 46960.5,
        "unexplained_share": 0.08569532043020564
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 13.83110693878333,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 13.83110693878333,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "c80014ffa5ce05bf0588ae0b087391152c5bca63552a7ed09201745e6685536c"
  }
}