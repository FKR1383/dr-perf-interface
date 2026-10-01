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
    "hypothesis": "The enormous cost concentrated in the unpenalized two-row stochastic state suggests initial compilation. A cold-cache indicator may isolate that cost and allow the remaining features to fit steady-state instructions.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "logits.numel()",
        "name": "logit_elements",
        "rationale": "Models batch-dependent baseline tensor processing."
      },
      {
        "expression": "logits.numel() if not sampling_metadata.all_greedy else 0",
        "name": "random_logit_elements",
        "rationale": "Models steady-state stochastic sampling and top-k/top-p work."
      },
      {
        "expression": "logits.numel() if not sampling_metadata.no_penalties else 0",
        "name": "penalized_logit_elements",
        "rationale": "Models vocabulary-wide penalty processing."
      },
      {
        "expression": "int(not sampling_metadata.all_greedy and (not torch._inductor.codecache.PyCodeCache.cache))",
        "name": "cold_random_compilation",
        "rationale": "Uses runtime cache emptiness to distinguish potentially expensive initial compilation from warm stochastic sampling."
      }
    ]
  },
  "case_id": "vllm-055",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 1,
    "case": "vllm-055",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 6",
      "workload return code 1"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 22.94863823056221,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "logit_elements",
      "random_logit_elements",
      "penalized_logit_elements",
      "cold_random_compilation"
    ],
    "raw_files": [
      "run.2352722.json"
    ],
    "required_states": 6,
    "returncode": 1,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 871943.0,
        "state": {
          "cold_random_compilation": 0,
          "logit_elements": 50272,
          "penalized_logit_elements": 0,
          "random_logit_elements": 0
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "73e1b2a01ca6fdec7ae22f87cbd54fa068b0c3201906791034d854c14e349916",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "workload return code 1",
        "insufficient state points: 1; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "success": false,
      "threshold_percent": 10.0,
      "valid": false
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": null,
      "iteration": 2,
      "reasons": [
        "workload return code 1",
        "insufficient state points: 1; need 6",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "73e1b2a01ca6fdec7ae22f87cbd54fa068b0c3201906791034d854c14e349916"
  }
}