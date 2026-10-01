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
    "hypothesis": "Instruction count is approximately a fixed setup cost plus a linear cost per generated float32 element.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "batch_size * num_channels_latents * ((num_frames - 1) // self.vae_scale_factor_temporal + 1) * (int(height) // self.vae_scale_factor_spatial) * (int(width) // self.vae_scale_factor_spatial) if latents is None else 0",
        "name": "generated_elements",
        "rationale": "CPU Gaussian sampling work scales with the number of generated latent elements; the remaining shape construction and dispatch work is approximately constant for this workload."
      }
    ]
  },
  "case_id": "wan-036",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 18,
    "case": "wan-036",
    "distinct_states": 5,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "generated_elements": 41.35029644268775
      },
      "constant": 33526.31027667985,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 11.970196007750928,
    "max_unexplained_share": 0.14268704431649512,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "generated_elements"
    ],
    "raw_files": [
      "run.1590486.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 42484.666666666664,
        "state": {
          "generated_elements": 64
        },
        "unexplained_instructions_per_call": 5832.0,
        "unexplained_share": 0.13727305537684184
      },
      {
        "calls": 6,
        "instructions_per_call": 44235.166666666664,
        "state": {
          "generated_elements": 128
        },
        "unexplained_instructions_per_call": 5832.0,
        "unexplained_share": 0.13184080539239143
      },
      {
        "calls": 3,
        "instructions_per_call": 49642.666666666664,
        "state": {
          "generated_elements": 256
        },
        "unexplained_instructions_per_call": 5832.0,
        "unexplained_share": 0.1174795874516545
      },
      {
        "calls": 3,
        "instructions_per_call": 87628.0,
        "state": {
          "generated_elements": 1024
        },
        "unexplained_instructions_per_call": 11664.0,
        "unexplained_share": 0.13310813895102022
      },
      {
        "calls": 3,
        "instructions_per_call": 122618.0,
        "state": {
          "generated_elements": 1728
        },
        "unexplained_instructions_per_call": 17496.0,
        "unexplained_share": 0.14268704431649512
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "32dbb465c78f01e116af8d7fca057e59845fce7f90efdd5f069280106b1cf723",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 14.268704431649512,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 14.268704431649512,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "32dbb465c78f01e116af8d7fca057e59845fce7f90efdd5f069280106b1cf723"
  }
}