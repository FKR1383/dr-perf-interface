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

This is iteration 5. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Minimum-token masking has substantial fixed overhead rather than cost proportional to tracked requests. Replacing the two dependent cardinalities with activation and singleton indicators should separate the expensive unpenalized cases while retaining the affine penalty model.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "int(not sampling_metadata.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures fixed penalty invocation overhead."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.no_penalties else 0",
        "name": "penalty_batch_size",
        "rationale": "Models the dominant linear growth of penalty operations."
      },
      {
        "expression": "int(sum((len(getattr(processor, 'logits_slice', ([], []))[0]) for processor in sampling_metadata.logitsprocs.non_argmax_invariant)) > 0)",
        "name": "minimum_token_mask_active",
        "rationale": "Captures the fixed cost of executing masking operations when minimum-token enforcement is active."
      },
      {
        "expression": "int(sum((len(getattr(processor, 'logits_slice', ([], []))[0]) for processor in sampling_metadata.logitsprocs.non_argmax_invariant)) == 1)",
        "name": "single_entry_minimum_token_mask",
        "rationale": "Distinguishes the observed single-entry masking case, whose cost exceeds the multi-entry case."
      }
    ]
  },
  "case_id": "vllm-054",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-054",
    "distinct_states": 15,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "minimum_token_mask_active": 18830.052204928666,
        "penalties_enabled": 346623.7844790317,
        "penalty_batch_size": 2643830.607003891,
        "single_entry_minimum_token_mask": 1393.3570038910507
      },
      "constant": 35838.24667098788,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 129.96801173035055,
    "max_unexplained_share": 0.3829683934553576,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "penalties_enabled",
      "penalty_batch_size",
      "minimum_token_mask_active",
      "single_entry_minimum_token_mask"
    ],
    "raw_files": [
      "run.2344372.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 5885.0,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 873.3333333333334,
        "unexplained_share": 0.14839988671764373
      },
      {
        "calls": 1,
        "instructions_per_call": 41496.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 7908.0,
        "unexplained_share": 0.19057258530942742
      },
      {
        "calls": 1,
        "instructions_per_call": 61791.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "single_entry_minimum_token_mask": 1
        },
        "unexplained_instructions_per_call": 23664.0,
        "unexplained_share": 0.3829683934553576
      },
      {
        "calls": 2,
        "instructions_per_call": 3811351.5,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 1,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 790927.0,
        "unexplained_share": 0.20751877647600858
      },
      {
        "calls": 4,
        "instructions_per_call": 7195857.0,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 2,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 1524746.0,
        "unexplained_share": 0.21189220408354417
      },
      {
        "calls": 3,
        "instructions_per_call": 10549855.0,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 2232895.0000000005,
        "unexplained_share": 0.21165172412322258
      },
      {
        "calls": 1,
        "instructions_per_call": 10657304.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 2295110.0,
        "unexplained_share": 0.21535559086988604
      },
      {
        "calls": 2,
        "instructions_per_call": 13884385.0,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 2924110.5,
        "unexplained_share": 0.21060425074643205
      },
      {
        "calls": 1,
        "instructions_per_call": 13918850.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 2934177.0,
        "unexplained_share": 0.210805993311229
      },
      {
        "calls": 2,
        "instructions_per_call": 17275611.0,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 3669295.0,
        "unexplained_share": 0.21239740811482732
      },
      {
        "calls": 1,
        "instructions_per_call": 17264314.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 3635047.0,
        "unexplained_share": 0.2105526463432025
      },
      {
        "calls": 1,
        "instructions_per_call": 20607052.0,
        "state": {
          "minimum_token_mask_active": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 4359082.0,
        "unexplained_share": 0.21153350804375123
      },
      {
        "calls": 1,
        "instructions_per_call": 20603325.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 4335650.0,
        "unexplained_share": 0.21043448084229124
      },
      {
        "calls": 1,
        "instructions_per_call": 23960359.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 1,
          "penalty_batch_size": 7,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 5045091.0,
        "unexplained_share": 0.21055990855562723
      },
      {
        "calls": 1,
        "instructions_per_call": 27300829.0,
        "state": {
          "minimum_token_mask_active": 1,
          "penalties_enabled": 1,
          "penalty_batch_size": 8,
          "single_entry_minimum_token_mask": 0
        },
        "unexplained_instructions_per_call": 5743743.0,
        "unexplained_share": 0.21038712780480037
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 38.29683934553576,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 38.29683934553576,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef"
  }
}