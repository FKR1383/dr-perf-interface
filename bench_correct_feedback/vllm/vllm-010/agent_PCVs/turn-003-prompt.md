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
    "hypothesis": "This workload consistently takes the no-new-full-blocks path, so instruction count should be approximately constant across token counts. A token-count PCV supplies the state diversity needed to test that hypothesis.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "num_tokens_to_cache",
        "name": "tokens_to_cache",
        "rationale": "Provides distinct entry states across prompt and decode lengths; the previous measurement showed that every call had zero newly completed cache blocks."
      }
    ]
  },
  "case_id": "vllm-010",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 88,
    "case": "vllm-010",
    "distinct_states": 15,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "tokens_to_cache": 0.0
      },
      "constant": 7017.443965707483,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 119.49203341593966,
    "max_unexplained_share": 0.18729482743323575,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "tokens_to_cache"
    ],
    "raw_files": [
      "run.2232629.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 6769.0,
        "state": {
          "tokens_to_cache": 9
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.0218643817402866
      },
      {
        "calls": 2,
        "instructions_per_call": 10430.0,
        "state": {
          "tokens_to_cache": 10
        },
        "unexplained_instructions_per_call": 996.0,
        "unexplained_share": 0.09549376797698945
      },
      {
        "calls": 1,
        "instructions_per_call": 11271.0,
        "state": {
          "tokens_to_cache": 11
        },
        "unexplained_instructions_per_call": 2111.0,
        "unexplained_share": 0.18729482743323575
      },
      {
        "calls": 1,
        "instructions_per_call": 6762.0,
        "state": {
          "tokens_to_cache": 12
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.02188701567583555
      },
      {
        "calls": 1,
        "instructions_per_call": 6796.0,
        "state": {
          "tokens_to_cache": 13
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.02177751618599176
      },
      {
        "calls": 4,
        "instructions_per_call": 6837.0,
        "state": {
          "tokens_to_cache": 21
        },
        "unexplained_instructions_per_call": 158.5,
        "unexplained_share": 0.023182682463068597
      },
      {
        "calls": 6,
        "instructions_per_call": 6776.166666666667,
        "state": {
          "tokens_to_cache": 22
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.021841257348058144
      },
      {
        "calls": 4,
        "instructions_per_call": 6787.5,
        "state": {
          "tokens_to_cache": 23
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.021804788213627992
      },
      {
        "calls": 3,
        "instructions_per_call": 6918.666666666667,
        "state": {
          "tokens_to_cache": 24
        },
        "unexplained_instructions_per_call": 178.66666666666669,
        "unexplained_share": 0.02582385816149547
      },
      {
        "calls": 1,
        "instructions_per_call": 7166.0,
        "state": {
          "tokens_to_cache": 25
        },
        "unexplained_instructions_per_call": 204.0,
        "unexplained_share": 0.028467764443204018
      },
      {
        "calls": 10,
        "instructions_per_call": 6758.7,
        "state": {
          "tokens_to_cache": 45
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.021897702220841288
      },
      {
        "calls": 21,
        "instructions_per_call": 6792.952380952381,
        "state": {
          "tokens_to_cache": 46
        },
        "unexplained_instructions_per_call": 152.38095238095238,
        "unexplained_share": 0.022432212657375994
      },
      {
        "calls": 17,
        "instructions_per_call": 6792.705882352941,
        "state": {
          "tokens_to_cache": 47
        },
        "unexplained_instructions_per_call": 153.41176470588235,
        "unexplained_share": 0.022584779521285805
      },
      {
        "calls": 11,
        "instructions_per_call": 6769.727272727273,
        "state": {
          "tokens_to_cache": 48
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.02186203284676434
      },
      {
        "calls": 5,
        "instructions_per_call": 6772.2,
        "state": {
          "tokens_to_cache": 49
        },
        "unexplained_instructions_per_call": 148.0,
        "unexplained_share": 0.021854050382445884
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "ecacc321a55fa07cb7cc03fd3e337574e0d78d7642b22a2040e5d86833c586a4",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 18.729482743323576,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 18.729482743323576,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "ecacc321a55fa07cb7cc03fd3e337574e0d78d7642b22a2040e5d86833c586a4"
  }
}