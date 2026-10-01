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
    "hypothesis": "Instruction count is dominated by fixed transformer overhead plus work proportional to text length, with an additional cost when the scheduler initializes its step index.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "prompt_embeds.shape[1]",
        "name": "text_length",
        "rationale": "Tracks text projection and cross-attention work in both transformer calls; latent dimensions and model size are fixed."
      },
      {
        "expression": "int(self.scheduler.step_index is None)",
        "name": "scheduler_initialization",
        "rationale": "Captures scheduler initialization performed on the first denoising step of each pipeline call."
      }
    ]
  },
  "case_id": "wan-026",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 39,
    "case": "wan-026",
    "distinct_states": 6,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "scheduler_initialization": 8021.472222222223,
        "text_length": 1502.8802083333348
      },
      "constant": 7100132.3472223235,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 25.268589215818793,
    "max_unexplained_share": 0.1581599256698508,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "text_length",
      "scheduler_initialization"
    ],
    "raw_files": [
      "run.1575059.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 8092656.333333333,
        "state": {
          "scheduler_initialization": 0,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 1049632.333333333,
        "unexplained_share": 0.12970182967117222
      },
      {
        "calls": 6,
        "instructions_per_call": 8640549.5,
        "state": {
          "scheduler_initialization": 1,
          "text_length": 4
        },
        "unexplained_instructions_per_call": 1366588.6666666665,
        "unexplained_share": 0.1581599256698508
      },
      {
        "calls": 6,
        "instructions_per_call": 8128821.0,
        "state": {
          "scheduler_initialization": 0,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 1055659.333333333,
        "unexplained_share": 0.12986622947329424
      },
      {
        "calls": 6,
        "instructions_per_call": 8145486.166666667,
        "state": {
          "scheduler_initialization": 1,
          "text_length": 8
        },
        "unexplained_instructions_per_call": 1063174.4999999998,
        "unexplained_share": 0.1305231484341317
      },
      {
        "calls": 12,
        "instructions_per_call": 8173709.666666667,
        "state": {
          "scheduler_initialization": 0,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 1064540.4166666667,
        "unexplained_share": 0.13023956808840245
      },
      {
        "calls": 6,
        "instructions_per_call": 8186645.0,
        "state": {
          "scheduler_initialization": 1,
          "text_length": 12
        },
        "unexplained_instructions_per_call": 1071275.6666666665,
        "unexplained_share": 0.13085649453062476
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "39be52c5c8b8b33c748dd1ce77571405e796a315d8b13bdd0fa573c1ad6905ca",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 15.815992566985079,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 15.815992566985079,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "39be52c5c8b8b33c748dd1ce77571405e796a315d8b13bdd0fa573c1ad6905ca"
  }
}