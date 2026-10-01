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

This is iteration 8. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Shared masking features coupled small unpenalized costs to much larger penalized costs. Branch-specific masking indicators should isolate the three observed unpenalized behaviors while leaving penalty costs affine in batch size.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "int(not sampling_metadata.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures fixed overhead specific to penalty execution."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.no_penalties else 0",
        "name": "penalty_batch_size",
        "rationale": "Models the nearly linear penalty cost across batch sizes."
      },
      {
        "expression": "int(sampling_metadata.no_penalties and sum((len(getattr(processor, 'logits_slice', ([], []))[0]) for processor in sampling_metadata.logitsprocs.non_argmax_invariant)) == 1)",
        "name": "unpenalized_single_mask",
        "rationale": "Separately models the expensive single-entry masking path without coupling its coefficient to penalized calls."
      },
      {
        "expression": "int(sampling_metadata.no_penalties and sum((len(getattr(processor, 'logits_slice', ([], []))[0]) for processor in sampling_metadata.logitsprocs.non_argmax_invariant)) > 1)",
        "name": "unpenalized_multiple_masks",
        "rationale": "Separates multi-entry masking from the inexpensive unpenalized baseline."
      }
    ]
  },
  "case_id": "vllm-054",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-054",
    "distinct_states": 11,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "penalties_enabled": 350067.1726190472,
        "penalty_batch_size": 2644753.280753967,
        "unpenalized_multiple_masks": 5655.666666666667,
        "unpenalized_single_mask": 11046.999999999998
      },
      "constant": 54060.228354976905,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 111.34574602264911,
    "max_unexplained_share": 0.25039058763511146,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "penalties_enabled",
      "penalty_batch_size",
      "unpenalized_single_mask",
      "unpenalized_multiple_masks"
    ],
    "raw_files": [
      "run.2347374.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 5955.333333333333,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 404.1666666666666,
        "unexplained_share": 0.06786633829620507
      },
      {
        "calls": 1,
        "instructions_per_call": 42113.0,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_multiple_masks": 1,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 5682.0,
        "unexplained_share": 0.13492270795241373
      },
      {
        "calls": 1,
        "instructions_per_call": 62726.0,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 1
        },
        "unexplained_instructions_per_call": 15706.0,
        "unexplained_share": 0.25039058763511146
      },
      {
        "calls": 2,
        "instructions_per_call": 3812008.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 1,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 769166.5,
        "unexplained_share": 0.2017746290144197
      },
      {
        "calls": 4,
        "instructions_per_call": 7195070.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 2,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 1501392.0,
        "unexplained_share": 0.20866954734283336
      },
      {
        "calls": 4,
        "instructions_per_call": 10577113.75,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 2216815.25,
        "unexplained_share": 0.20958602719007347
      },
      {
        "calls": 3,
        "instructions_per_call": 13894574.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 2902459.666666667,
        "unexplained_share": 0.20889159082291167
      },
      {
        "calls": 3,
        "instructions_per_call": 17272141.666666668,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 3634091.9999999995,
        "unexplained_share": 0.2104019333637934
      },
      {
        "calls": 2,
        "instructions_per_call": 20605279.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 4322870.5,
        "unexplained_share": 0.2097943201836772
      },
      {
        "calls": 1,
        "instructions_per_call": 23960226.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 7,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 5019664.0,
        "unexplained_share": 0.20949986031016568
      },
      {
        "calls": 1,
        "instructions_per_call": 27303144.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 8,
          "unpenalized_multiple_masks": 0,
          "unpenalized_single_mask": 0
        },
        "unexplained_instructions_per_call": 5719078.0,
        "unexplained_share": 0.20946591352263313
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 25.039058763511147,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 25.039058763511147,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef"
  }
}