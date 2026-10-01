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
    "hypothesis": "All 36 calls followed the same empty-search regime, suggesting approximately constant instruction cost. Request length supplies distinct state points to test that hypothesis, with its coefficient expected to be small.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "request.num_tokens",
        "name": "request_tokens",
        "rationale": "Provides varying entry states across prompt lengths when every observed lookup has zero eligible cache blocks."
      }
    ]
  },
  "case_id": "vllm-012",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "vllm-012",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "request_tokens": -3.569617893755825
      },
      "constant": 19548.86950528114,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 94.73352425079793,
    "max_unexplained_share": 0.27771810132094643,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "request_tokens"
    ],
    "raw_files": [
      "run.2237938.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 18667.0,
        "state": {
          "request_tokens": 9
        },
        "unexplained_instructions_per_call": 821.0,
        "unexplained_share": 0.04398135747575936
      },
      {
        "calls": 1,
        "instructions_per_call": 34445.0,
        "state": {
          "request_tokens": 10
        },
        "unexplained_instructions_per_call": 9566.0,
        "unexplained_share": 0.27771810132094643
      },
      {
        "calls": 1,
        "instructions_per_call": 30123.0,
        "state": {
          "request_tokens": 11
        },
        "unexplained_instructions_per_call": 6924.0,
        "unexplained_share": 0.22985758390598546
      },
      {
        "calls": 4,
        "instructions_per_call": 18722.0,
        "state": {
          "request_tokens": 21
        },
        "unexplained_instructions_per_call": 842.5,
        "unexplained_share": 0.04500053413096891
      },
      {
        "calls": 3,
        "instructions_per_call": 19178.0,
        "state": {
          "request_tokens": 22
        },
        "unexplained_instructions_per_call": 1019.6666666666665,
        "unexplained_share": 0.05316856119859561
      },
      {
        "calls": 10,
        "instructions_per_call": 18669.6,
        "state": {
          "request_tokens": 45
        },
        "unexplained_instructions_per_call": 821.0,
        "unexplained_share": 0.04397523246347003
      },
      {
        "calls": 12,
        "instructions_per_call": 18810.5,
        "state": {
          "request_tokens": 46
        },
        "unexplained_instructions_per_call": 874.6666666666667,
        "unexplained_share": 0.046498852591194635
      },
      {
        "calls": 4,
        "instructions_per_call": 18777.0,
        "state": {
          "request_tokens": 47
        },
        "unexplained_instructions_per_call": 885.5,
        "unexplained_share": 0.04715875805506737
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e1acd78660be84b1b47a6d96d8d4c03c5fdd651749ce9623fed34c26dd704977",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 27.771810132094643,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 27.771810132094643,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e1acd78660be84b1b47a6d96d8d4c03c5fdd651749ce9623fed34c26dd704977"
  }
}