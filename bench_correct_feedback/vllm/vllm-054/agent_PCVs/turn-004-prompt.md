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
    "hypothesis": "A well-scaled gated batch-size model should capture the nearly affine penalty cost. Unpenalized batch size and empty-history cardinality should explain variation hidden by the previous all-zero unpenalized state.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "int(not sampling_metadata.no_penalties)",
        "name": "penalties_enabled",
        "rationale": "Captures fixed overhead from invoking penalty operations."
      },
      {
        "expression": "logits.shape[0] if not sampling_metadata.no_penalties else 0",
        "name": "penalty_batch_size",
        "rationale": "Penalty instruction counts grow nearly linearly with batch size at the fixed vocabulary size; this avoids large feature magnitudes."
      },
      {
        "expression": "logits.shape[0] if sampling_metadata.no_penalties else 0",
        "name": "unpenalized_batch_size",
        "rationale": "Separates batch-dependent processor work in the previously collapsed unpenalized observations."
      },
      {
        "expression": "sum((int(len(row) == 0) for row in sampling_metadata.output_token_ids))",
        "name": "requests_without_output",
        "rationale": "Tracks requests on their first sampling step, when minimum-token processing can suppress stopping tokens."
      }
    ]
  },
  "case_id": "vllm-054",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-054",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "penalties_enabled": 333424.0757854427,
        "penalty_batch_size": 3315006.99545977,
        "requests_without_output": 643.4193103448272,
        "unpenalized_batch_size": -158.49999999833705
      },
      "constant": 96712.76775040351,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 140.0928635261953,
    "max_unexplained_share": 0.35684362765877864,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "penalties_enabled",
      "penalty_batch_size",
      "unpenalized_batch_size",
      "requests_without_output"
    ],
    "raw_files": [
      "run.2342112.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 4,
        "instructions_per_call": 20051.5,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "requests_without_output": 0,
          "unpenalized_batch_size": 1
        },
        "unexplained_instructions_per_call": 7155.25,
        "unexplained_share": 0.35684362765877864
      },
      {
        "calls": 4,
        "instructions_per_call": 14918.75,
        "state": {
          "penalties_enabled": 0,
          "penalty_batch_size": 0,
          "requests_without_output": 0,
          "unpenalized_batch_size": 2
        },
        "unexplained_instructions_per_call": 2792.0,
        "unexplained_share": 0.1871470465018852
      },
      {
        "calls": 2,
        "instructions_per_call": 3810925.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 1,
          "requests_without_output": 0,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 147090.0,
        "unexplained_share": 0.03859692856721137
      },
      {
        "calls": 4,
        "instructions_per_call": 7194786.5,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 2,
          "requests_without_output": 0,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 252100.75,
        "unexplained_share": 0.03503936496239325
      },
      {
        "calls": 3,
        "instructions_per_call": 10550282.666666666,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "requests_without_output": 0,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 268078.6666666666,
        "unexplained_share": 0.025409619356802065
      },
      {
        "calls": 1,
        "instructions_per_call": 10660631.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 3,
          "requests_without_output": 3,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 240770.0,
        "unexplained_share": 0.022584967062456246
      },
      {
        "calls": 2,
        "instructions_per_call": 13882321.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "requests_without_output": 0,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 168658.0,
        "unexplained_share": 0.012149121173613548
      },
      {
        "calls": 1,
        "instructions_per_call": 13916775.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 4,
          "requests_without_output": 4,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 180832.0,
        "unexplained_share": 0.012993815018206446
      },
      {
        "calls": 2,
        "instructions_per_call": 17274619.5,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "requests_without_output": 0,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 466439.5,
        "unexplained_share": 0.027001434098157705
      },
      {
        "calls": 1,
        "instructions_per_call": 17263368.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 5,
          "requests_without_output": 5,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 142149.0,
        "unexplained_share": 0.00823414063814199
      },
      {
        "calls": 1,
        "instructions_per_call": 20605691.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "requests_without_output": 0,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 345352.0,
        "unexplained_share": 0.01676003003247986
      },
      {
        "calls": 1,
        "instructions_per_call": 20602395.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 6,
          "requests_without_output": 6,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 140761.0,
        "unexplained_share": 0.006832263918830796
      },
      {
        "calls": 1,
        "instructions_per_call": 23959256.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 7,
          "requests_without_output": 7,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 156827.0,
        "unexplained_share": 0.006545570530236832
      },
      {
        "calls": 1,
        "instructions_per_call": 27301350.0,
        "state": {
          "penalties_enabled": 1,
          "penalty_batch_size": 8,
          "requests_without_output": 8,
          "unpenalized_batch_size": 0
        },
        "unexplained_instructions_per_call": 152163.0,
        "unexplained_share": 0.005573460653044629
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 35.684362765877864,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 35.684362765877864,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e4fa03508e373c9a42701d2acc9ab03530118e537f0e53059f73b1f095a2a7ef"
  }
}