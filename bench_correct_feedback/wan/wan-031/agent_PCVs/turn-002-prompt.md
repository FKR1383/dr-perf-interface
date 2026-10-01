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
    "hypothesis": "Instruction count is explained by per-prompt overhead, linear padded-token processing, quadratic attention work, and input text length.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "1 if isinstance(prompt, str) else len(prompt)",
        "name": "batch_size",
        "rationale": "Captures per-prompt cleaning, tokenization, slicing, and padding overhead."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length",
        "name": "token_positions",
        "rationale": "Models encoder projections and elementwise work on padded tokens."
      },
      {
        "expression": "(1 if isinstance(prompt, str) else len(prompt)) * max_sequence_length ** 2",
        "name": "attention_pairs",
        "rationale": "Models quadratic attention and relative-position processing."
      },
      {
        "expression": "len(prompt) if isinstance(prompt, str) else sum((len(p) for p in prompt))",
        "name": "prompt_characters",
        "rationale": "Captures text-dependent cleaning and tokenizer work using cheap string lengths."
      }
    ]
  },
  "case_id": "wan-031",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-031",
    "distinct_states": 11,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "attention_pairs": -1204.9744675108323,
        "batch_size": -48644.712014134966,
        "prompt_characters": 120.88810365135451,
        "token_positions": 32242.983271496912
      },
      "constant": 2354185.827423204,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 30.00343069108203,
    "max_unexplained_share": 0.32720314528921596,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "batch_size",
      "token_positions",
      "attention_pairs",
      "prompt_characters"
    ],
    "raw_files": [
      "run.1580241.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 3270898.3333333335,
        "state": {
          "attention_pairs": 64,
          "batch_size": 1,
          "prompt_characters": 4,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 823830.1666666665,
        "unexplained_share": 0.2518666380642626
      },
      {
        "calls": 3,
        "instructions_per_call": 3750709.6666666665,
        "state": {
          "attention_pairs": 64,
          "batch_size": 1,
          "prompt_characters": 8,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 1227244.0,
        "unexplained_share": 0.32720314528921596
      },
      {
        "calls": 3,
        "instructions_per_call": 3279060.6666666665,
        "state": {
          "attention_pairs": 64,
          "batch_size": 1,
          "prompt_characters": 14,
          "token_positions": 8
        },
        "unexplained_instructions_per_call": 825517.9999999998,
        "unexplained_share": 0.25175441503471213
      },
      {
        "calls": 3,
        "instructions_per_call": 3373064.3333333335,
        "state": {
          "attention_pairs": 144,
          "batch_size": 1,
          "prompt_characters": 4,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 875335.0000000002,
        "unexplained_share": 0.2595073539955212
      },
      {
        "calls": 3,
        "instructions_per_call": 3380289.3333333335,
        "state": {
          "attention_pairs": 144,
          "batch_size": 1,
          "prompt_characters": 13,
          "token_positions": 12
        },
        "unexplained_instructions_per_call": 875773.3333333334,
        "unexplained_share": 0.25908235863044465
      },
      {
        "calls": 3,
        "instructions_per_call": 3352855.6666666665,
        "state": {
          "attention_pairs": 256,
          "batch_size": 1,
          "prompt_characters": 4,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 864223.3333333334,
        "unexplained_share": 0.25775739228063005
      },
      {
        "calls": 3,
        "instructions_per_call": 3368357.0,
        "state": {
          "attention_pairs": 256,
          "batch_size": 1,
          "prompt_characters": 21,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 868960.3333333335,
        "unexplained_share": 0.25797750456181856
      },
      {
        "calls": 3,
        "instructions_per_call": 3586383.0,
        "state": {
          "attention_pairs": 128,
          "batch_size": 2,
          "prompt_characters": 8,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 946952.6666666671,
        "unexplained_share": 0.26404114303092197
      },
      {
        "calls": 3,
        "instructions_per_call": 3551481.6666666665,
        "state": {
          "attention_pairs": 128,
          "batch_size": 2,
          "prompt_characters": 17,
          "token_positions": 16
        },
        "unexplained_instructions_per_call": 907072.6666666667,
        "unexplained_share": 0.25540682785447766
      },
      {
        "calls": 3,
        "instructions_per_call": 3637573.0,
        "state": {
          "attention_pairs": 512,
          "batch_size": 2,
          "prompt_characters": 8,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 932434.3333333329,
        "unexplained_share": 0.2563341913229873
      },
      {
        "calls": 3,
        "instructions_per_call": 3653352.6666666665,
        "state": {
          "attention_pairs": 512,
          "batch_size": 2,
          "prompt_characters": 24,
          "token_positions": 32
        },
        "unexplained_instructions_per_call": 938133.9999999998,
        "unexplained_share": 0.25678714473956243
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 32.7203145289216,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 32.7203145289216,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "fddc047f7f9267b71c7fbce739fac243e934efaa850fcdec3c9c73e857561b14"
  }
}