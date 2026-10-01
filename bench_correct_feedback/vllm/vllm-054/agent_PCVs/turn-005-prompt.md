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
    "hypothesis": "Remaining irregularity is concentrated in inexpensive unpenalized calls. Minimum-token processor entry state should distinguish their tracking and masking work more directly than batch size or penalty output histories.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "int(not sampling_metadata.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures fixed penalty invocation overhead."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.no_penalties else 0",
        "name": "penalty_batch_size",
        "rationale": "Retains the feature that explained penalized calls to within 4 percent."
      },
      {
        "expression": "sum((len(getattr(processor, 'min_toks', {})) for processor in sampling_metadata.logitsprocs.non_argmax_invariant))",
        "name": "minimum_token_tracked_requests",
        "rationale": "Measures minimum-token processor tracking state, which can vary even when penalty metadata contains no output histories."
      },
      {
        "expression": "sum((len(getattr(processor, 'logits_slice', ([], []))[0]) for processor in sampling_metadata.logitsprocs.non_argmax_invariant))",
        "name": "minimum_token_mask_entries",
        "rationale": "Measures cached masking-index cardinality associated with minimum-token enforcement."
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
        "minimum_token_mask_entries": 0.0,
        "minimum_token_tracked_requests": 616.4986699600993,
        "penalties_enabled": 315591.25316148344,
        "penalty_batch_size": 2643673.688541074
      },
      "constant": 57777.92747059796,
      "dependent_columns": [
        3
      ]
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 140.18234025407583,
    "max_unexplained_share": 0.44464230787910186,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "penalties_enabled",
      "penalty_batch_size",
      "minimum_token_tracked_requests",
      "minimum_token_mask_entries"
    ],
    "raw_files": [
      "run.2343119.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 6,
        "instructions_per_call": 5798.5,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 0,
          "penalty_batch_size": 0
        },
        "unexplained_instructions_per_call": 1056.5,
        "unexplained_share": 0.18220229369664567
      },
      {
        "calls": 1,
        "instructions_per_call": 61771.0,
        "state": {
          "minimum_token_mask_entries": 1,
          "minimum_token_tracked_requests": 1,
          "penalties_enabled": 0,
          "penalty_batch_size": 0
        },
        "unexplained_instructions_per_call": 27466.0,
        "unexplained_share": 0.44464230787910186
      },
      {
        "calls": 1,
        "instructions_per_call": 40742.0,
        "state": {
          "minimum_token_mask_entries": 2,
          "minimum_token_tracked_requests": 2,
          "penalties_enabled": 0,
          "penalty_batch_size": 0
        },
        "unexplained_instructions_per_call": 9612.0,
        "unexplained_share": 0.23592361690638652
      },
      {
        "calls": 2,
        "instructions_per_call": 3810464.5,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 1
        },
        "unexplained_instructions_per_call": 803733.0,
        "unexplained_share": 0.2109278278278147
      },
      {
        "calls": 4,
        "instructions_per_call": 7194662.75,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 2
        },
        "unexplained_instructions_per_call": 1537309.0,
        "unexplained_share": 0.21367353181356555
      },
      {
        "calls": 3,
        "instructions_per_call": 10549254.666666666,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 3
        },
        "unexplained_instructions_per_call": 2245909.3333333335,
        "unexplained_share": 0.21289744198041924
      },
      {
        "calls": 1,
        "instructions_per_call": 10659274.0,
        "state": {
          "minimum_token_mask_entries": 3,
          "minimum_token_tracked_requests": 3,
          "penalties_enabled": 1,
          "penalty_batch_size": 3
        },
        "unexplained_instructions_per_call": 2314709.0,
        "unexplained_share": 0.2171544703701209
      },
      {
        "calls": 2,
        "instructions_per_call": 13883551.5,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 4
        },
        "unexplained_instructions_per_call": 2936882.0,
        "unexplained_share": 0.21153679589836938
      },
      {
        "calls": 1,
        "instructions_per_call": 13919653.0,
        "state": {
          "minimum_token_mask_entries": 4,
          "minimum_token_tracked_requests": 4,
          "penalties_enabled": 1,
          "penalty_batch_size": 4
        },
        "unexplained_instructions_per_call": 2949575.0,
        "unexplained_share": 0.2119000380253732
      },
      {
        "calls": 2,
        "instructions_per_call": 17274288.5,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 5
        },
        "unexplained_instructions_per_call": 3681712.5,
        "unexplained_share": 0.21313251194108515
      },
      {
        "calls": 1,
        "instructions_per_call": 17262768.0,
        "state": {
          "minimum_token_mask_entries": 5,
          "minimum_token_tracked_requests": 5,
          "penalties_enabled": 1,
          "penalty_batch_size": 5
        },
        "unexplained_instructions_per_call": 3649661.0,
        "unexplained_share": 0.21141806458848314
      },
      {
        "calls": 1,
        "instructions_per_call": 20606009.0,
        "state": {
          "minimum_token_mask_entries": 0,
          "minimum_token_tracked_requests": 0,
          "penalties_enabled": 1,
          "penalty_batch_size": 6
        },
        "unexplained_instructions_per_call": 4371723.0,
        "unexplained_share": 0.21215767691841733
      },
      {
        "calls": 1,
        "instructions_per_call": 20601930.0,
        "state": {
          "minimum_token_mask_entries": 6,
          "minimum_token_tracked_requests": 6,
          "penalties_enabled": 1,
          "penalty_batch_size": 6
        },
        "unexplained_instructions_per_call": 4349087.0,
        "unexplained_share": 0.21110095025077746
      },
      {
        "calls": 1,
        "instructions_per_call": 23960183.0,
        "state": {
          "minimum_token_mask_entries": 7,
          "minimum_token_tracked_requests": 7,
          "penalties_enabled": 1,
          "penalty_batch_size": 7
        },
        "unexplained_instructions_per_call": 5059814.0,
        "unexplained_share": 0.21117593300518614
      },
      {
        "calls": 1,
        "instructions_per_call": 27299972.0,
        "state": {
          "minimum_token_mask_entries": 8,
          "minimum_token_tracked_requests": 8,
          "penalties_enabled": 1,
          "penalty_batch_size": 8
        },
        "unexplained_instructions_per_call": 5757736.0,
        "unexplained_share": 0.21090629690023124
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 44.46423078791019,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 44.46423078791019,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef"
  }
}