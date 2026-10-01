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
    "hypothesis": "Instruction count is approximately constant across this workload; text length and denoising step count do not change the work within each region invocation.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "latents.shape[0] * (latents.shape[2] * ((latents.shape[3] + 1) // 2) * ((latents.shape[4] + 1) // 2) if self.config.expand_timesteps else 1)",
        "name": "timestep_elements",
        "rationale": "The fixture keeps expansion disabled, batch size fixed, and latent dtype equal to transformer dtype, so the region performs a dtype-preserving conversion and a fixed-size expand with approximately constant instruction count."
      }
    ]
  },
  "case_id": "wan-029",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 39,
    "case": "wan-029",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 3"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 13.3775645759888,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "timestep_elements"
    ],
    "raw_files": [
      "run.1578312.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 39,
        "instructions_per_call": 14759.948717948719,
        "state": {
          "timestep_elements": 1
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "9d32790b8cd59b63dd4bc6c3ba0f173e4fe2ad571dae306802a33f55ffaf1ab9",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 1; need 3",
        "Dr. Perf did not produce an irregularity value"
      ],
      "success": false,
      "threshold_percent": 10.0,
      "valid": false
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": null,
      "iteration": 1,
      "reasons": [
        "insufficient state points: 1; need 3",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "9d32790b8cd59b63dd4bc6c3ba0f173e4fe2ad571dae306802a33f55ffaf1ab9"
  }
}