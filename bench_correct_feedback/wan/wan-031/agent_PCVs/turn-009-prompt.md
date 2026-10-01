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
    "hypothesis": "Cache state substantially improved the previous result. Encoding its observed cold-to-warm transition as a binary feature should improve numerical conditioning while preserving the same explanatory information.",
    "iteration": 5,
    "pcvs": [
      {
        "expression": "int(len(re._main._cache) < 15)",
        "name": "regex_cache_cold",
        "rationale": "The observed cache grows from 14 to 15 entries during the first call. A binary cold-cache feature represents that transition without a large constant offset."
      },
      {
        "expression": "1 if isinstance(prompt, str) else len(prompt)",
        "name": "batch_size",
        "rationale": "Captures per-prompt cleaning, tokenization, and embedding reconstruction overhead."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length",
        "name": "token_positions",
        "rationale": "Models encoder processing over padded sequences."
      },
      {
        "expression": "len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))",
        "name": "prompt_characters",
        "rationale": "Captures input-dependent cleaning and tokenization work."
      }
    ]
  },
  "case_id": "wan-031",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-031",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "batch_size": 169150.35921860984,
        "prompt_characters": 109.5326402981984,
        "regex_cache_cold": 845528.2755974331,
        "token_positions": 2757.2469472630614
      },
      "constant": 2874801.4886762877,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 30.20273622404784,
    "max_unexplained_share": 0.12031889733962473,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "regex_cache_cold",
      "batch_size",
      "token_positions",
      "prompt_characters"
    ],
    "raw_files": [
      "run.1583388.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3273248.1666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "regex_cache_cold": 0,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 215973.49999999997,
        "unexplained_share": 0.06598140104358112
      },
      {
        "calls": 2,
        "instructions_per_call": 3485824.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 8,
          "regex_cache_cold": 0,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 419410.5,
        "unexplained_share": 0.12031889733962473
      },
      {
        "calls": 3,
        "instructions_per_call": 3281175.6666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 14,
          "regex_cache_cold": 0,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 216419.3333333333,
        "unexplained_share": 0.06595786246129055
      },
      {
        "calls": 3,
        "instructions_per_call": 3372321.6666666665,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "regex_cache_cold": 0,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 301884.00000000006,
        "unexplained_share": 0.08951815094744325
      },
      {
        "calls": 3,
        "instructions_per_call": 3381431.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 13,
          "regex_cache_cold": 0,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 303119.6666666667,
        "unexplained_share": 0.08964242259169762
      },
      {
        "calls": 3,
        "instructions_per_call": 3355240.3333333335,
        "state": {
          "batch_size": 1,
          "prompt_characters": 4,
          "regex_cache_cold": 0,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 273909.6666666666,
        "unexplained_share": 0.08163637756301807
      },
      {
        "calls": 3,
        "instructions_per_call": 3370764.3333333335,
        "state": {
          "batch_size": 1,
          "prompt_characters": 21,
          "regex_cache_cold": 0,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 276882.3333333333,
        "unexplained_share": 0.08214229947648866
      },
      {
        "calls": 3,
        "instructions_per_call": 3592368.6666666665,
        "state": {
          "batch_size": 2,
          "prompt_characters": 8,
          "regex_cache_cold": 0,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 330469.33333333343,
        "unexplained_share": 0.0919920431329153
      },
      {
        "calls": 3,
        "instructions_per_call": 3558614.3333333335,
        "state": {
          "batch_size": 2,
          "prompt_characters": 17,
          "regex_cache_cold": 0,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 288921.0,
        "unexplained_share": 0.08118918571582591
      },
      {
        "calls": 3,
        "instructions_per_call": 3635291.6666666665,
        "state": {
          "batch_size": 2,
          "prompt_characters": 8,
          "regex_cache_cold": 0,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 336705.6666666667,
        "unexplained_share": 0.09262136233910623
      },
      {
        "calls": 3,
        "instructions_per_call": 3650545.6666666665,
        "state": {
          "batch_size": 2,
          "prompt_characters": 24,
          "regex_cache_cold": 0,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 340540.3333333333,
        "unexplained_share": 0.09328477560021392
      },
      {
        "calls": 1,
        "instructions_per_call": 4277705.0,
        "state": {
          "batch_size": 1,
          "prompt_characters": 8,
          "regex_cache_cold": 1,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 358842.0,
        "unexplained_share": 0.08388657001826914
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14",
  "iteration": 5,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 12.031889733962473,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 12.031889733962473,
      "iteration": 5,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14"
  }
}