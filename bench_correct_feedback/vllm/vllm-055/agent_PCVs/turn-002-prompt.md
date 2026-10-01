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
    "hypothesis": "Instruction count is primarily explained by batch size, the fixed and batch-dependent costs of stochastic sampling, and whether vocabulary-wide penalties are applied.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "logits.numel()",
        "name": "logit_elements",
        "rationale": "Captures batch-dependent greedy sampling and tensor processing."
      },
      {
        "expression": "int(not sampling_metadata.all_greedy)",
        "name": "random_sampling",
        "rationale": "Captures fixed overhead from entering temperature scaling and stochastic sampling."
      },
      {
        "expression": "logits.numel() if not sampling_metadata.all_greedy else 0",
        "name": "random_logit_elements",
        "rationale": "Captures vocabulary-wide top-k/top-p processing and random sampling across the batch."
      },
      {
        "expression": "logits.numel() if not sampling_metadata.no_penalties else 0",
        "name": "penalized_logit_elements",
        "rationale": "Captures vocabulary-wide repetition, presence, and frequency penalty processing."
      }
    ]
  },
  "case_id": "vllm-055",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-055",
    "distinct_states": 13,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "logit_elements": 26.646169645761194,
        "penalized_logit_elements": 43.28317632331683,
        "random_logit_elements": 65.64237452181436,
        "random_sampling": 291940.92129836784
      },
      "constant": -226283.09467521598,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 150.86829973384738,
    "max_unexplained_share": 0.9976422338389441,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "logit_elements",
      "random_sampling",
      "random_logit_elements",
      "penalized_logit_elements"
    ],
    "raw_files": [
      "run.2351671.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 819613.6666666666,
        "state": {
          "logit_elements": 50272,
          "penalized_logit_elements": 0,
          "random_logit_elements": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 96837.00000000003,
        "unexplained_share": 0.11814956721479758
      },
      {
        "calls": 2,
        "instructions_per_call": 4596472.0,
        "state": {
          "logit_elements": 50272,
          "penalized_logit_elements": 50272,
          "random_logit_elements": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 1110961.5,
        "unexplained_share": 0.24169874199168406
      },
      {
        "calls": 1,
        "instructions_per_call": 31493775.0,
        "state": {
          "logit_elements": 50272,
          "penalized_logit_elements": 0,
          "random_logit_elements": 50272,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 27076536.0,
        "unexplained_share": 0.859742472917267
      },
      {
        "calls": 2,
        "instructions_per_call": 8803837.5,
        "state": {
          "logit_elements": 100544,
          "penalized_logit_elements": 100544,
          "random_logit_elements": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 1965546.5,
        "unexplained_share": 0.22326019761268878
      },
      {
        "calls": 4,
        "instructions_per_call": 4259585690.0,
        "state": {
          "logit_elements": 100544,
          "penalized_logit_elements": 0,
          "random_logit_elements": 100544,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 4249542583.0,
        "unexplained_share": 0.9976422338389441
      },
      {
        "calls": 2,
        "instructions_per_call": 49123404.0,
        "state": {
          "logit_elements": 100544,
          "penalized_logit_elements": 100544,
          "random_logit_elements": 100544,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 35175953.0,
        "unexplained_share": 0.7160731980218634
      },
      {
        "calls": 1,
        "instructions_per_call": 12907692.0,
        "state": {
          "logit_elements": 150816,
          "penalized_logit_elements": 150816,
          "random_logit_elements": 0,
          "random_sampling": 0
        },
        "unexplained_instructions_per_call": 2720330.0,
        "unexplained_share": 0.21075262719314963
      },
      {
        "calls": 3,
        "instructions_per_call": 71581754.66666667,
        "state": {
          "logit_elements": 150816,
          "penalized_logit_elements": 150816,
          "random_logit_elements": 150816,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 50897113.00000008,
        "unexplained_share": 0.7110347215852929
      },
      {
        "calls": 3,
        "instructions_per_call": 93350224.66666667,
        "state": {
          "logit_elements": 201088,
          "penalized_logit_elements": 201088,
          "random_logit_elements": 201088,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 65953115.0,
        "unexplained_share": 0.7065126542062884
      },
      {
        "calls": 3,
        "instructions_per_call": 117288209.33333333,
        "state": {
          "logit_elements": 251360,
          "penalized_logit_elements": 251360,
          "random_logit_elements": 251360,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 83158446.3333333,
        "unexplained_share": 0.7090094290466727
      },
      {
        "calls": 2,
        "instructions_per_call": 139660654.5,
        "state": {
          "logit_elements": 301632,
          "penalized_logit_elements": 301632,
          "random_logit_elements": 301632,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 98811760.5,
        "unexplained_share": 0.707513228072406
      },
      {
        "calls": 1,
        "instructions_per_call": 162176892.0,
        "state": {
          "logit_elements": 351904,
          "penalized_logit_elements": 351904,
          "random_logit_elements": 351904,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 114599033.0,
        "unexplained_share": 0.7066298508174642
      },
      {
        "calls": 1,
        "instructions_per_call": 185139964.0,
        "state": {
          "logit_elements": 402176,
          "penalized_logit_elements": 402176,
          "random_logit_elements": 402176,
          "random_sampling": 1
        },
        "unexplained_instructions_per_call": 130841953.0,
        "unexplained_share": 0.7067191230522223
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "73e1b2a01ca6fdec7ae22f87cbd54fa068b0c3201906791034d854c14e349916",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 99.76422338389442,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 99.76422338389442,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "73e1b2a01ca6fdec7ae22f87cbd54fa068b0c3201906791034d854c14e349916"
  }
}