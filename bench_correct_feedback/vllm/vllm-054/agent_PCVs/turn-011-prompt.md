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
    "hypothesis": "Empty-history state may be essential to the successful penalty attribution in iteration 2. Restoring it while using a compact batch-sensitive masking feature should address both penalized and unpenalized variation within four expressions.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "int(not sampling_metadata.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures fixed penalty overhead."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.no_penalties else 0",
        "name": "penalty_batch_size",
        "rationale": "Models dense penalty work proportional to batch size."
      },
      {
        "expression": "sum((int(len(row) == 0) for row in sampling_metadata.output_token_ids))",
        "name": "requests_without_output",
        "rationale": "Restores the empty-history feature from iteration 2, which achieved less than 4 percent unexplained work on penalized calls."
      },
      {
        "expression": "sum((int(len(getattr(processor, 'logits_slice', ([], []))[0]) > 0) for processor in sampling_metadata.logitsprocs.non_argmax_invariant)) * (1 + 2 // logits.shape[0]) if sampling_metadata.no_penalties else 0",
        "name": "unpenalized_mask_batch_factor",
        "rationale": "Combines masking activation with a larger singleton-batch factor, approximating the observed masking overhead in one feature."
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
        "penalties_enabled": 336800.0111220593,
        "penalty_batch_size": 3315065.9458374386,
        "requests_without_output": 640.1876190476196,
        "unpenalized_mask_batch_factor": 1753.2857142857208
      },
      "constant": 90275.43919867818,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 135.79857301153243,
    "max_unexplained_share": 0.41060941873068774,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "penalties_enabled",
      "penalty_batch_size",
      "requests_without_output",
      "unpenalized_mask_batch_factor"
    ],
    "raw_files": [
      "run.2349317.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 5866.666666666667,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 965.3333333333336,
        "unexplained_share": 0.16454545454545458
      },
      {
        "calls": 1,
        "instructions_per_call": 40803.0,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 2
        },
        "unexplained_instructions_per_call": 7712.0,
        "unexplained_share": 0.18900571036443398
      },
      {
        "calls": 1,
        "instructions_per_call": 61813.0,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 3
        },
        "unexplained_instructions_per_call": 25381.0,
        "unexplained_share": 0.41060941873068774
      },
      {
        "calls": 2,
        "instructions_per_call": 3813353.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 1,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 149466.5,
        "unexplained_share": 0.03919555834458546
      },
      {
        "calls": 4,
        "instructions_per_call": 7197356.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 2,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 254142.25,
        "unexplained_share": 0.0353105015230593
      },
      {
        "calls": 3,
        "instructions_per_call": 10551665.333333334,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 270303.0,
        "unexplained_share": 0.025617093744064918
      },
      {
        "calls": 1,
        "instructions_per_call": 10661597.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "requests_without_output": 3,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 241182.0,
        "unexplained_share": 0.022621564105264905
      },
      {
        "calls": 2,
        "instructions_per_call": 13886707.5,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 171634.0,
        "unexplained_share": 0.012359589197079293
      },
      {
        "calls": 1,
        "instructions_per_call": 13918503.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "requests_without_output": 4,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 182468.0,
        "unexplained_share": 0.01310974319580202
      },
      {
        "calls": 2,
        "instructions_per_call": 17277300.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 468648.0,
        "unexplained_share": 0.02712507162577486
      },
      {
        "calls": 1,
        "instructions_per_call": 17266154.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "requests_without_output": 5,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 144249.0,
        "unexplained_share": 0.008354437241785287
      },
      {
        "calls": 1,
        "instructions_per_call": 20608765.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "requests_without_output": 0,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 347431.0,
        "unexplained_share": 0.016858409516533376
      },
      {
        "calls": 1,
        "instructions_per_call": 20604517.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "requests_without_output": 6,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 142600.0,
        "unexplained_share": 0.006920812557751293
      },
      {
        "calls": 1,
        "instructions_per_call": 23960638.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 7,
          "requests_without_output": 7,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 157993.0,
        "unexplained_share": 0.0065938561402246465
      },
      {
        "calls": 1,
        "instructions_per_call": 27302678.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 8,
          "requests_without_output": 8,
          "unpenalized_mask_batch_factor": 0
        },
        "unexplained_instructions_per_call": 154356.0,
        "unexplained_share": 0.0056535113515238326
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 41.06094187306877,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 41.06094187306877,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef"
  }
}