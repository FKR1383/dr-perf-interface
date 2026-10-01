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
    "hypothesis": "The remaining underprediction grows with query length, including for aligned key lengths. A quadratic query term may capture this growth better than the linear key/value term while retaining the observed key-tail effect.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * key.shape[1]",
        "name": "attention_pairs",
        "rationale": "Tracks attention matrix arithmetic."
      },
      {
        "expression": "query.numel()",
        "name": "query_elements",
        "rationale": "Tracks linear per-query processing."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] ** 2",
        "name": "quadratic_query_work",
        "rationale": "Tests the additional nonlinear growth with query length visible in both self-attention and cross-attention."
      },
      {
        "expression": "query.shape[0] * query.shape[2] * query.shape[1] * (key.shape[1] % 16)",
        "name": "scalar_tail_pairs",
        "rationale": "Retains the remainder feature that reduced irregularity from 47.1% to 27.8%."
      }
    ]
  },
  "case_id": "wan-019",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-019",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "attention_pairs": 0.04060856809130023,
        "quadratic_query_work": 4.522058224055876,
        "query_elements": 1.0987280688714074,
        "scalar_tail_pairs": 37.16982846814686
      },
      "constant": 128721.04122009974,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 15.064406433142722,
    "max_unexplained_share": 0.27400818086427625,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "attention_pairs",
      "query_elements",
      "quadratic_query_work",
      "scalar_tail_pairs"
    ],
    "raw_files": [
      "run.1565861.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 142990.0,
        "state": {
          "attention_pairs": 144,
          "quadratic_query_work": 324,
          "query_elements": 288,
          "scalar_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 10326.666666666666,
        "unexplained_share": 0.0722195025293144
      },
      {
        "calls": 3,
        "instructions_per_call": 164828.33333333334,
        "state": {
          "attention_pairs": 324,
          "quadratic_query_work": 324,
          "query_elements": 288,
          "scalar_tail_pairs": 324
        },
        "unexplained_instructions_per_call": 18484.0,
        "unexplained_share": 0.11214091428455868
      },
      {
        "calls": 3,
        "instructions_per_call": 168752.33333333334,
        "state": {
          "attention_pairs": 384,
          "quadratic_query_work": 1024,
          "query_elements": 512,
          "scalar_tail_pairs": 384
        },
        "unexplained_instructions_per_call": 21408.666666666664,
        "unexplained_share": 0.1268644186648283
      },
      {
        "calls": 3,
        "instructions_per_call": 195305.66666666666,
        "state": {
          "attention_pairs": 512,
          "quadratic_query_work": 4096,
          "query_elements": 1024,
          "scalar_tail_pairs": 512
        },
        "unexplained_instructions_per_call": 28784.0,
        "unexplained_share": 0.1473792363082143
      },
      {
        "calls": 3,
        "instructions_per_call": 191627.33333333334,
        "state": {
          "attention_pairs": 648,
          "quadratic_query_work": 1296,
          "query_elements": 576,
          "scalar_tail_pairs": 648
        },
        "unexplained_instructions_per_call": 32406.0,
        "unexplained_share": 0.16910948681642493
      },
      {
        "calls": 3,
        "instructions_per_call": 201184.33333333334,
        "state": {
          "attention_pairs": 648,
          "quadratic_query_work": 2916,
          "query_elements": 864,
          "scalar_tail_pairs": 648
        },
        "unexplained_instructions_per_call": 33765.0,
        "unexplained_share": 0.16783115981529376
      },
      {
        "calls": 3,
        "instructions_per_call": 143942.66666666666,
        "state": {
          "attention_pairs": 1024,
          "quadratic_query_work": 1024,
          "query_elements": 512,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 11969.666666666668,
        "unexplained_share": 0.08315579351037915
      },
      {
        "calls": 3,
        "instructions_per_call": 161047.66666666666,
        "state": {
          "attention_pairs": 1296,
          "quadratic_query_work": 1296,
          "query_elements": 576,
          "scalar_tail_pairs": 144
        },
        "unexplained_instructions_per_call": 21534.333333333332,
        "unexplained_share": 0.13371403497515227
      },
      {
        "calls": 3,
        "instructions_per_call": 319747.3333333333,
        "state": {
          "attention_pairs": 1728,
          "quadratic_query_work": 9216,
          "query_elements": 1536,
          "scalar_tail_pairs": 1728
        },
        "unexplained_instructions_per_call": 82398.66666666666,
        "unexplained_share": 0.2576993084122672
      },
      {
        "calls": 3,
        "instructions_per_call": 256044.66666666666,
        "state": {
          "attention_pairs": 2916,
          "quadratic_query_work": 2916,
          "query_elements": 864,
          "scalar_tail_pairs": 1188
        },
        "unexplained_instructions_per_call": 70158.33333333333,
        "unexplained_share": 0.27400818086427625
      },
      {
        "calls": 3,
        "instructions_per_call": 178012.66666666666,
        "state": {
          "attention_pairs": 4096,
          "quadratic_query_work": 4096,
          "query_elements": 1024,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 32598.333333333332,
        "unexplained_share": 0.18312367284725056
      },
      {
        "calls": 3,
        "instructions_per_call": 247454.66666666666,
        "state": {
          "attention_pairs": 9216,
          "quadratic_query_work": 9216,
          "query_elements": 1536,
          "scalar_tail_pairs": 0
        },
        "unexplained_instructions_per_call": 67680.33333333333,
        "unexplained_share": 0.2735059889757585
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 27.400818086427627,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 27.400818086427627,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "a74487487c642fe4275bdcfa02bb98f8966583ee5eac5e976522509b7e5751eb"
  }
}