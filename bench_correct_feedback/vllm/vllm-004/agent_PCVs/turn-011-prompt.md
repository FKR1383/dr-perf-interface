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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The derived workload predictors have consistently failed. Testing the four raw workload dimensions may reveal dependence on per-request query and context lengths that aggregation and rounding concealed.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens",
        "name": "query_tokens",
        "rationale": "Measures total query rows processed."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.max_query_len",
        "name": "max_query_length",
        "rationale": "Exposes per-request query length directly, which aggregate token counts and rounded tiles obscure."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.max_seq_len",
        "name": "max_context_length",
        "rationale": "Exposes the unrounded context dimension used by attention loops."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel()",
        "name": "requests",
        "rationale": "Separates batch cardinality from per-request dimensions."
      }
    ]
  },
  "case_id": "vllm-004",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 336,
    "case": "vllm-004",
    "distinct_states": 25,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "max_context_length": 0.0,
        "max_query_length": 75.87153843168798,
        "query_tokens": 3691.9125807960395,
        "requests": 1289.0113120669814
      },
      "constant": 90643.23963513819,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 101.26148733636364,
    "max_unexplained_share": 0.7939630581548646,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_tokens",
      "max_query_length",
      "max_context_length",
      "requests"
    ],
    "raw_files": [
      "run.1799187.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 12,
        "instructions_per_call": 124231.66666666667,
        "state": {
          "max_context_length": 13,
          "max_query_length": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 28526.0,
        "unexplained_share": 0.22961939387434765
      },
      {
        "calls": 12,
        "instructions_per_call": 122950.25,
        "state": {
          "max_context_length": 24,
          "max_query_length": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 27845.583333333332,
        "unexplained_share": 0.22647846046131123
      },
      {
        "calls": 12,
        "instructions_per_call": 122909.33333333333,
        "state": {
          "max_context_length": 25,
          "max_query_length": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 27809.416666666668,
        "unexplained_share": 0.22625960057277997
      },
      {
        "calls": 12,
        "instructions_per_call": 138818.83333333334,
        "state": {
          "max_context_length": 48,
          "max_query_length": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 43419.25,
        "unexplained_share": 0.31277636439820244
      },
      {
        "calls": 12,
        "instructions_per_call": 138670.5,
        "state": {
          "max_context_length": 49,
          "max_query_length": 1,
          "query_tokens": 1,
          "requests": 1
        },
        "unexplained_instructions_per_call": 43378.333333333336,
        "unexplained_share": 0.31281587167662434
      },
      {
        "calls": 12,
        "instructions_per_call": 153479.08333333334,
        "state": {
          "max_context_length": 12,
          "max_query_length": 1,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 52673.333333333336,
        "unexplained_share": 0.3431955168701055
      },
      {
        "calls": 24,
        "instructions_per_call": 151847.16666666666,
        "state": {
          "max_context_length": 23,
          "max_query_length": 1,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 51351.49999999999,
        "unexplained_share": 0.33817884868886805
      },
      {
        "calls": 12,
        "instructions_per_call": 151625.75,
        "state": {
          "max_context_length": 24,
          "max_query_length": 1,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 51226.0,
        "unexplained_share": 0.33784499004951335
      },
      {
        "calls": 24,
        "instructions_per_call": 183163.33333333334,
        "state": {
          "max_context_length": 48,
          "max_query_length": 1,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 82792.83333333333,
        "unexplained_share": 0.4520164152213871
      },
      {
        "calls": 12,
        "instructions_per_call": 182914.16666666666,
        "state": {
          "max_context_length": 49,
          "max_query_length": 1,
          "query_tokens": 2,
          "requests": 2
        },
        "unexplained_instructions_per_call": 82659.99999999999,
        "unexplained_share": 0.4519059486006642
      },
      {
        "calls": 12,
        "instructions_per_call": 180259.0,
        "state": {
          "max_context_length": 22,
          "max_query_length": 1,
          "query_tokens": 3,
          "requests": 3
        },
        "unexplained_instructions_per_call": 75274.58333333333,
        "unexplained_share": 0.41759126220234954
      },
      {
        "calls": 24,
        "instructions_per_call": 227395.625,
        "state": {
          "max_context_length": 47,
          "max_query_length": 1,
          "query_tokens": 3,
          "requests": 3
        },
        "unexplained_instructions_per_call": 122269.29166666667,
        "unexplained_share": 0.5376941252351125
      },
      {
        "calls": 12,
        "instructions_per_call": 271703.8333333333,
        "state": {
          "max_context_length": 48,
          "max_query_length": 1,
          "query_tokens": 4,
          "requests": 4
        },
        "unexplained_instructions_per_call": 161548.3333333333,
        "unexplained_share": 0.5945750980080639
      },
      {
        "calls": 12,
        "instructions_per_call": 271775.6666666667,
        "state": {
          "max_context_length": 49,
          "max_query_length": 1,
          "query_tokens": 4,
          "requests": 4
        },
        "unexplained_instructions_per_call": 161551.1666666667,
        "unexplained_share": 0.5944283704574974
      },
      {
        "calls": 12,
        "instructions_per_call": 315050.1666666667,
        "state": {
          "max_context_length": 46,
          "max_query_length": 1,
          "query_tokens": 5,
          "requests": 5
        },
        "unexplained_instructions_per_call": 200322.83333333334,
        "unexplained_share": 0.6358442385630648
      },
      {
        "calls": 12,
        "instructions_per_call": 315164.6666666667,
        "state": {
          "max_context_length": 47,
          "max_query_length": 1,
          "query_tokens": 5,
          "requests": 5
        },
        "unexplained_instructions_per_call": 200125.91666666666,
        "unexplained_share": 0.6349884293290068
      },
      {
        "calls": 12,
        "instructions_per_call": 358708.5833333333,
        "state": {
          "max_context_length": 48,
          "max_query_length": 1,
          "query_tokens": 6,
          "requests": 6
        },
        "unexplained_instructions_per_call": 239142.75,
        "unexplained_share": 0.6666769659586717
      },
      {
        "calls": 12,
        "instructions_per_call": 281031.3333333333,
        "state": {
          "max_context_length": 10,
          "max_query_length": 10,
          "query_tokens": 10,
          "requests": 1
        },
        "unexplained_instructions_per_call": 135914.08333333337,
        "unexplained_share": 0.4836260843986556
      },
      {
        "calls": 12,
        "instructions_per_call": 446292.0,
        "state": {
          "max_context_length": 11,
          "max_query_length": 11,
          "query_tokens": 20,
          "requests": 2
        },
        "unexplained_instructions_per_call": 279046.9166666667,
        "unexplained_share": 0.625256371762583
      },
      {
        "calls": 12,
        "instructions_per_call": 1149328.5,
        "state": {
          "max_context_length": 22,
          "max_query_length": 22,
          "query_tokens": 66,
          "requests": 3
        },
        "unexplained_instructions_per_call": 809411.25,
        "unexplained_share": 0.7042470886260978
      },
      {
        "calls": 12,
        "instructions_per_call": 1478153.4166666667,
        "state": {
          "max_context_length": 21,
          "max_query_length": 21,
          "query_tokens": 84,
          "requests": 4
        },
        "unexplained_instructions_per_call": 1071198.0,
        "unexplained_share": 0.7246866177230926
      },
      {
        "calls": 12,
        "instructions_per_call": 4391233.916666667,
        "state": {
          "max_context_length": 46,
          "max_query_length": 46,
          "query_tokens": 230,
          "requests": 5
        },
        "unexplained_instructions_per_call": 3443082.6666666665,
        "unexplained_share": 0.7840809057332726
      },
      {
        "calls": 12,
        "instructions_per_call": 5212744.166666667,
        "state": {
          "max_context_length": 45,
          "max_query_length": 45,
          "query_tokens": 270,
          "requests": 6
        },
        "unexplained_instructions_per_call": 4115697.5000000005,
        "unexplained_share": 0.7895452699018256
      },
      {
        "calls": 12,
        "instructions_per_call": 6103560.0,
        "state": {
          "max_context_length": 46,
          "max_query_length": 46,
          "query_tokens": 322,
          "requests": 7
        },
        "unexplained_instructions_per_call": 4813433.083333333,
        "unexplained_share": 0.7886271427385547
      },
      {
        "calls": 12,
        "instructions_per_call": 7092625.333333333,
        "state": {
          "max_context_length": 47,
          "max_query_length": 47,
          "query_tokens": 368,
          "requests": 8
        },
        "unexplained_instructions_per_call": 5631282.499999999,
        "unexplained_share": 0.7939630581548646
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 79.39630581548646,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 79.39630581548646,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}