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
    "hypothesis": "Instruction count should be approximately fixed setup cost plus per-step cost and per-step text-token cost, since this workload supplies embeddings directly and returns latents without VAE decoding.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "num_inference_steps",
        "name": "denoising_steps",
        "rationale": "Each step repeats two transformer calls, classifier-free guidance, and a scheduler update; latent dimensions and model configuration are fixed in this workload."
      },
      {
        "expression": "num_inference_steps * prompt_embeds.shape[1]",
        "name": "step_text_tokens",
        "rationale": "Text projection and cross-attention work scale with the supplied embedding sequence length on every denoising step."
      }
    ]
  },
  "case_id": "wan-025",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 18,
    "case": "wan-025",
    "distinct_states": 6,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "denoising_steps": 7153199.210062905,
        "step_text_tokens": 7559.489622641505
      },
      "constant": 10409780.967715073,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 27.28876710589975,
    "max_unexplained_share": 0.17040900640285034,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "denoising_steps",
      "step_text_tokens"
    ],
    "raw_files": [
      "run.1574037.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 21919665.0,
        "state": {
          "denoising_steps": 1,
          "step_text_tokens": 4
        },
        "unexplained_instructions_per_call": 3735308.3333333344,
        "unexplained_share": 0.17040900640285034
      },
      {
        "calls": 3,
        "instructions_per_call": 20287767.333333332,
        "state": {
          "denoising_steps": 1,
          "step_text_tokens": 8
        },
        "unexplained_instructions_per_call": 2974815.6666666656,
        "unexplained_share": 0.14663100270175938
      },
      {
        "calls": 3,
        "instructions_per_call": 28340168.0,
        "state": {
          "denoising_steps": 2,
          "step_text_tokens": 8
        },
        "unexplained_instructions_per_call": 3734118.000000003,
        "unexplained_share": 0.13176061623911342
      },
      {
        "calls": 3,
        "instructions_per_call": 28514164.333333332,
        "state": {
          "denoising_steps": 2,
          "step_text_tokens": 24
        },
        "unexplained_instructions_per_call": 3787832.3333333316,
        "unexplained_share": 0.13284037677040808
      },
      {
        "calls": 3,
        "instructions_per_call": 36551919.333333336,
        "state": {
          "denoising_steps": 3,
          "step_text_tokens": 24
        },
        "unexplained_instructions_per_call": 4542432.333333335,
        "unexplained_share": 0.12427342848699294
      },
      {
        "calls": 3,
        "instructions_per_call": 44855698.0,
        "state": {
          "denoising_steps": 4,
          "step_text_tokens": 48
        },
        "unexplained_instructions_per_call": 5367698.999999999,
        "unexplained_share": 0.1196659340804372
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "27359e61ef134af714c23c0befcb1d3a221123d691a7f2d9347de7190de65960",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 17.040900640285034,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 17.040900640285034,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "27359e61ef134af714c23c0befcb1d3a221123d691a7f2d9347de7190de65960"
  }
}