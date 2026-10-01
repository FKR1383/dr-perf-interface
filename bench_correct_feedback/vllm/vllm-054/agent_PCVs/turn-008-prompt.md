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

This is iteration 7. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Disjoint penalized and unpenalized batch features produced substantially better attribution in iteration 2. Combining that exact basis with actual minimum-token masking state tests whether both sources of variation can be explained together.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "int(not sampling_metadata.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures fixed penalty invocation overhead."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.no_penalties else 0",
        "name": "penalty_batch_size",
        "rationale": "Preserves the penalty feature used in the best-performing penalty fit."
      },
      {
        "expression": "logits.shape[0] if sampling_metadata.no_penalties else 0",
        "name": "unpenalized_batch_size",
        "rationale": "Restores the disjoint batch features from iteration 2 so their fitted contributions remain specific to each branch."
      },
      {
        "expression": "sum((len(getattr(processor, 'logits_slice', ([], []))[0]) for processor in sampling_metadata.logitsprocs.non_argmax_invariant))",
        "name": "minimum_token_mask_entries",
        "rationale": "Separates masked and unmasked unpenalized calls, which empty penalty histories could not distinguish."
      }
    ]
  },
  "case_id": "vllm-054",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-054",
    "distinct_states": 16,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "minimum_token_mask_entries": 822.3995291902069,
        "penalties_enabled": 317650.36577213067,
        "penalty_batch_size": 2643840.3611581884,
        "unpenalized_batch_size": -193.68662900038606
      },
      "constant": 55486.021557204374,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 137.37099488917738,
    "max_unexplained_share": 0.4280918011515692,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "penalties_enabled",
      "penalty_batch_size",
      "unpenalized_batch_size",
      "minimum_token_mask_entries"
    ],
    "raw_files": [
      "run.2346435.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 5773.0,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_batch_size": 1
        },
        "unexplained_instructions_per_call": 919.9999999999999,
        "unexplained_share": 0.15936254980079678
      },
      {
        "calls": 1,
        "instructions_per_call": 61655.0,
        "state": {
          "minimum_token_mask_entries": 1,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_batch_size": 1
        },
        "unexplained_instructions_per_call": 26394.0,
        "unexplained_share": 0.4280918011515692
      },
      {
        "calls": 3,
        "instructions_per_call": 5810.0,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_batch_size": 2
        },
        "unexplained_instructions_per_call": 937.0,
        "unexplained_share": 0.1612736660929432
      },
      {
        "calls": 1,
        "instructions_per_call": 40541.0,
        "state": {
          "minimum_token_mask_entries": 2,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "unpenalized_batch_size": 2
        },
        "unexplained_instructions_per_call": 8625.0,
        "unexplained_share": 0.2127475888606596
      },
      {
        "calls": 2,
        "instructions_per_call": 3810379.0,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 1,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 799395.0,
        "unexplained_share": 0.2097940913489183
      },
      {
        "calls": 4,
        "instructions_per_call": 7194732.75,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 2,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 1533037.25,
        "unexplained_share": 0.2130777199472767
      },
      {
        "calls": 3,
        "instructions_per_call": 10549421.666666666,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 2241449.666666666,
        "unexplained_share": 0.2124713313668221
      },
      {
        "calls": 1,
        "instructions_per_call": 10656808.0,
        "state": {
          "minimum_token_mask_entries": 3,
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 2307905.0,
        "unexplained_share": 0.2165662551112866
      },
      {
        "calls": 2,
        "instructions_per_call": 13883701.5,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 2932441.0,
        "unexplained_share": 0.21121463897794115
      },
      {
        "calls": 1,
        "instructions_per_call": 13915347.0,
        "state": {
          "minimum_token_mask_entries": 4,
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 2942588.0,
        "unexplained_share": 0.21146350141322384
      },
      {
        "calls": 2,
        "instructions_per_call": 17275251.0,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 3678198.5,
        "unexplained_share": 0.21291722476275454
      },
      {
        "calls": 1,
        "instructions_per_call": 17263363.0,
        "state": {
          "minimum_token_mask_entries": 5,
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 3645288.0,
        "unexplained_share": 0.211157466827292
      },
      {
        "calls": 1,
        "instructions_per_call": 20605641.0,
        "state": {
          "minimum_token_mask_entries": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 4366210.0,
        "unexplained_share": 0.21189391778688177
      },
      {
        "calls": 1,
        "instructions_per_call": 20602951.0,
        "state": {
          "minimum_token_mask_entries": 6,
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 4345107.0,
        "unexplained_share": 0.21089731271991086
      },
      {
        "calls": 1,
        "instructions_per_call": 23959553.0,
        "state": {
          "minimum_token_mask_entries": 7,
          "penalties_enabled": 1,
          "penalty_batch_size": 7,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 5054497.0,
        "unexplained_share": 0.21095957007211277
      },
      {
        "calls": 1,
        "instructions_per_call": 27301291.0,
        "state": {
          "minimum_token_mask_entries": 8,
          "penalties_enabled": 1,
          "penalty_batch_size": 8,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 5753822.0,
        "unexplained_share": 0.2107527442566727
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 42.80918011515692,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 42.80918011515692,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef"
  }
}