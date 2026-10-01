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

This is iteration 7. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Each workload state aggregates twelve layer calls. Persistent underprediction despite several plausible size models may reflect first-layer costs hidden within those aggregates; layer-conditioned predictors test that possibility.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "0 if attn_metadata is None else attn_metadata.num_actual_tokens",
        "name": "query_tokens",
        "rationale": "Retains the principal token-dependent work predictor."
      },
      {
        "expression": "0 if attn_metadata is None else attn_metadata.seq_lens.numel() * ((attn_metadata.max_seq_len + 31) // 32)",
        "name": "request_blocks",
        "rationale": "Captures request overhead and block-rounded decode work."
      },
      {
        "expression": "0 if attn_metadata is None or '.0.' not in layer.layer_name else attn_metadata.num_actual_tokens",
        "name": "first_layer_query_tokens",
        "rationale": "Tests whether the first decoder layer incurs additional token-dependent initialization or dispatch work."
      },
      {
        "expression": "0 if attn_metadata is None or '.0.' not in layer.layer_name else attn_metadata.seq_lens.numel() * ((attn_metadata.max_seq_len + 31) // 32)",
        "name": "first_layer_request_blocks",
        "rationale": "Separates possible first-layer request and kernel setup costs from subsequent layers."
      }
    ]
  },
  "case_id": "vllm-004",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 336,
    "case": "vllm-004",
    "distinct_states": 34,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "first_layer_query_tokens": 0.0,
        "first_layer_request_blocks": 0.0,
        "query_tokens": 3665.6691042992934,
        "request_blocks": 300.50535616349987
      },
      "constant": 65229.697513058396,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 126.02362585999072,
    "max_unexplained_share": 0.8002077583541901,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_tokens",
      "request_blocks",
      "first_layer_query_tokens",
      "first_layer_request_blocks"
    ],
    "raw_files": [
      "run.1797370.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 33,
        "instructions_per_call": 123351.30303030302,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 1,
          "request_blocks": 1
        },
        "unexplained_instructions_per_call": 55591.57575757579,
        "unexplained_share": 0.450676842415835
      },
      {
        "calls": 3,
        "instructions_per_call": 123347.66666666667,
        "state": {
          "first_layer_query_tokens": 1,
          "first_layer_request_blocks": 1,
          "query_tokens": 1,
          "request_blocks": 1
        },
        "unexplained_instructions_per_call": 55539.00000000001,
        "unexplained_share": 0.450263888250825
      },
      {
        "calls": 22,
        "instructions_per_call": 138538.68181818182,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 1,
          "request_blocks": 2
        },
        "unexplained_instructions_per_call": 70638.59090909091,
        "unexplained_share": 0.509883521208878
      },
      {
        "calls": 2,
        "instructions_per_call": 138345.5,
        "state": {
          "first_layer_query_tokens": 1,
          "first_layer_request_blocks": 2,
          "query_tokens": 1,
          "request_blocks": 2
        },
        "unexplained_instructions_per_call": 70434.5,
        "unexplained_share": 0.5091202821920482
      },
      {
        "calls": 44,
        "instructions_per_call": 152085.25,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 2,
          "request_blocks": 2
        },
        "unexplained_instructions_per_call": 80031.18181818178,
        "unexplained_share": 0.5262257965067735
      },
      {
        "calls": 4,
        "instructions_per_call": 152699.5,
        "state": {
          "first_layer_query_tokens": 2,
          "first_layer_request_blocks": 2,
          "query_tokens": 2,
          "request_blocks": 2
        },
        "unexplained_instructions_per_call": 80287.0,
        "unexplained_share": 0.5257843018477467
      },
      {
        "calls": 33,
        "instructions_per_call": 182964.0909090909,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 2,
          "request_blocks": 4
        },
        "unexplained_instructions_per_call": 110641.7575757576,
        "unexplained_share": 0.604718428769348
      },
      {
        "calls": 3,
        "instructions_per_call": 182669.66666666666,
        "state": {
          "first_layer_query_tokens": 2,
          "first_layer_request_blocks": 4,
          "query_tokens": 2,
          "request_blocks": 4
        },
        "unexplained_instructions_per_call": 110350.0,
        "unexplained_share": 0.6040959181327314
      },
      {
        "calls": 11,
        "instructions_per_call": 180425.81818181818,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 3,
          "request_blocks": 3
        },
        "unexplained_instructions_per_call": 104369.36363636368,
        "unexplained_share": 0.5784613570724612
      },
      {
        "calls": 1,
        "instructions_per_call": 180120.0,
        "state": {
          "first_layer_query_tokens": 3,
          "first_layer_request_blocks": 3,
          "query_tokens": 3,
          "request_blocks": 3
        },
        "unexplained_instructions_per_call": 104058.0,
        "unexplained_share": 0.5777148567621586
      },
      {
        "calls": 22,
        "instructions_per_call": 227427.22727272726,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 3,
          "request_blocks": 6
        },
        "unexplained_instructions_per_call": 150901.49999999997,
        "unexplained_share": 0.6635155421344568
      },
      {
        "calls": 2,
        "instructions_per_call": 227161.0,
        "state": {
          "first_layer_query_tokens": 3,
          "first_layer_request_blocks": 6,
          "query_tokens": 3,
          "request_blocks": 6
        },
        "unexplained_instructions_per_call": 150604.0,
        "unexplained_share": 0.6629835226997592
      },
      {
        "calls": 22,
        "instructions_per_call": 271407.45454545453,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 4,
          "request_blocks": 8
        },
        "unexplained_instructions_per_call": 190651.3636363635,
        "unexplained_share": 0.7024544110465241
      },
      {
        "calls": 2,
        "instructions_per_call": 271080.5,
        "state": {
          "first_layer_query_tokens": 4,
          "first_layer_request_blocks": 8,
          "query_tokens": 4,
          "request_blocks": 8
        },
        "unexplained_instructions_per_call": 190337.0,
        "unexplained_share": 0.7021419836543019
      },
      {
        "calls": 22,
        "instructions_per_call": 314938.7727272727,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 5,
          "request_blocks": 10
        },
        "unexplained_instructions_per_call": 229979.04545454547,
        "unexplained_share": 0.7302341450784158
      },
      {
        "calls": 2,
        "instructions_per_call": 314831.0,
        "state": {
          "first_layer_query_tokens": 5,
          "first_layer_request_blocks": 10,
          "query_tokens": 5,
          "request_blocks": 10
        },
        "unexplained_instructions_per_call": 229863.0,
        "unexplained_share": 0.730115522296089
      },
      {
        "calls": 11,
        "instructions_per_call": 358847.45454545453,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 6,
          "request_blocks": 12
        },
        "unexplained_instructions_per_call": 269719.54545454547,
        "unexplained_share": 0.751627305803783
      },
      {
        "calls": 1,
        "instructions_per_call": 358205.0,
        "state": {
          "first_layer_query_tokens": 6,
          "first_layer_request_blocks": 12,
          "query_tokens": 6,
          "request_blocks": 12
        },
        "unexplained_instructions_per_call": 269110.0,
        "unexplained_share": 0.7512737119805698
      },
      {
        "calls": 11,
        "instructions_per_call": 261551.0,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 10,
          "request_blocks": 1
        },
        "unexplained_instructions_per_call": 159853.54545454553,
        "unexplained_share": 0.611175432151074
      },
      {
        "calls": 1,
        "instructions_per_call": 494168.0,
        "state": {
          "first_layer_query_tokens": 10,
          "first_layer_request_blocks": 1,
          "query_tokens": 10,
          "request_blocks": 1
        },
        "unexplained_instructions_per_call": 346631.0,
        "unexplained_share": 0.7014436386006379
      },
      {
        "calls": 11,
        "instructions_per_call": 446006.1818181818,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 20,
          "request_blocks": 2
        },
        "unexplained_instructions_per_call": 307781.727272727,
        "unexplained_share": 0.6900839939438257
      },
      {
        "calls": 1,
        "instructions_per_call": 445926.0,
        "state": {
          "first_layer_query_tokens": 20,
          "first_layer_request_blocks": 2,
          "query_tokens": 20,
          "request_blocks": 2
        },
        "unexplained_instructions_per_call": 307744.0,
        "unexplained_share": 0.6901234734014163
      },
      {
        "calls": 11,
        "instructions_per_call": 1149354.7272727273,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 66,
          "request_blocks": 3
        },
        "unexplained_instructions_per_call": 842015.2727272724,
        "unexplained_share": 0.7325982594818813
      },
      {
        "calls": 1,
        "instructions_per_call": 1148975.0,
        "state": {
          "first_layer_query_tokens": 66,
          "first_layer_request_blocks": 3,
          "query_tokens": 66,
          "request_blocks": 3
        },
        "unexplained_instructions_per_call": 841754.0,
        "unexplained_share": 0.7326129811353598
      },
      {
        "calls": 11,
        "instructions_per_call": 1477973.1818181819,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 84,
          "request_blocks": 4
        },
        "unexplained_instructions_per_call": 1104467.272727273,
        "unexplained_share": 0.747285056531657
      },
      {
        "calls": 1,
        "instructions_per_call": 1477877.0,
        "state": {
          "first_layer_query_tokens": 84,
          "first_layer_request_blocks": 4,
          "query_tokens": 84,
          "request_blocks": 4
        },
        "unexplained_instructions_per_call": 1104388.0,
        "unexplained_share": 0.7472800510461967
      },
      {
        "calls": 11,
        "instructions_per_call": 4391315.7272727275,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 230,
          "request_blocks": 10
        },
        "unexplained_instructions_per_call": 3481491.000000001,
        "unexplained_share": 0.792812727715713
      },
      {
        "calls": 1,
        "instructions_per_call": 4390723.0,
        "state": {
          "first_layer_query_tokens": 230,
          "first_layer_request_blocks": 10,
          "query_tokens": 230,
          "request_blocks": 10
        },
        "unexplained_instructions_per_call": 3480976.0,
        "unexplained_share": 0.7928024610069914
      },
      {
        "calls": 11,
        "instructions_per_call": 5212975.636363637,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 270,
          "request_blocks": 12
        },
        "unexplained_instructions_per_call": 4156087.5454545445,
        "unexplained_share": 0.7972581948135988
      },
      {
        "calls": 1,
        "instructions_per_call": 5213330.0,
        "state": {
          "first_layer_query_tokens": 270,
          "first_layer_request_blocks": 12,
          "query_tokens": 270,
          "request_blocks": 12
        },
        "unexplained_instructions_per_call": 4156475.0,
        "unexplained_share": 0.7972783230679815
      },
      {
        "calls": 11,
        "instructions_per_call": 6103502.363636363,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 322,
          "request_blocks": 14
        },
        "unexplained_instructions_per_call": 4855482.6363636395,
        "unexplained_share": 0.7955240036100888
      },
      {
        "calls": 1,
        "instructions_per_call": 6103258.0,
        "state": {
          "first_layer_query_tokens": 322,
          "first_layer_request_blocks": 14,
          "query_tokens": 322,
          "request_blocks": 14
        },
        "unexplained_instructions_per_call": 4855324.0,
        "unexplained_share": 0.7955298629027316
      },
      {
        "calls": 11,
        "instructions_per_call": 7092418.0,
        "state": {
          "first_layer_query_tokens": 0,
          "first_layer_request_blocks": 0,
          "query_tokens": 368,
          "request_blocks": 16
        },
        "unexplained_instructions_per_call": 5675407.909090908,
        "unexplained_share": 0.8002077583541901
      },
      {
        "calls": 1,
        "instructions_per_call": 7091802.0,
        "state": {
          "first_layer_query_tokens": 368,
          "first_layer_request_blocks": 16,
          "query_tokens": 368,
          "request_blocks": 16
        },
        "unexplained_instructions_per_call": 5674816.0,
        "unexplained_share": 0.8001938012369776
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 80.02077583541902,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 80.02077583541902,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "8d28eaa0f80112e4370cf9be1174b36e2fbf1692710b5768c08fef9143446f6a"
  }
}