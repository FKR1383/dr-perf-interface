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
    "hypothesis": "Independent self-attention and cross-attention work estimates may explain their different scaling better than shared token slopes. Combining linear and quadratic work also captures increasing marginal cost at larger sequence lengths.",
    "iteration": 3,
    "pcvs": [
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Separates fixed rotary operator overhead from the cross-attention baseline."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * (hidden_states.shape[1] + 2 * attn.inner_dim) if encoder_hidden_states is None else 0",
        "name": "self_attention_work",
        "rationale": "Combines quadratic attention work with linear projection work, giving self-attention an independent fitted coefficient."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] * encoder_hidden_states.shape[1] + attn.inner_dim * (hidden_states.shape[1] + encoder_hidden_states.shape[1])) if encoder_hidden_states is not None else 0",
        "name": "cross_attention_work",
        "rationale": "Captures cross-attention pair work and query/context projection work independently of self-attention."
      },
      {
        "expression": "hidden_states.shape[0] * (hidden_states.shape[1] % 16) if encoder_hidden_states is None else 0",
        "name": "self_attention_tail",
        "rationale": "Retains a separate feature for the apparent self-attention remainder cost."
      }
    ]
  },
  "case_id": "wan-017",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-017",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "cross_attention_work": 11.555205248956932,
        "self_attention_tail": 73.62896930346027,
        "self_attention_work": 9.37018293456428,
        "uses_rotary": 323756.048740348
      },
      "constant": 630346.9489721201,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.605225889012218,
    "max_unexplained_share": 0.2570283158843776,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "uses_rotary",
      "self_attention_work",
      "cross_attention_work",
      "self_attention_tail"
    ],
    "raw_files": [
      "run.1560083.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 681960.6666666666,
        "state": {
          "cross_attention_work": 452,
          "self_attention_tail": 0,
          "self_attention_work": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 51975.333333333336,
        "unexplained_share": 0.07621456173914234
      },
      {
        "calls": 3,
        "instructions_per_call": 714711.3333333334,
        "state": {
          "cross_attention_work": 800,
          "self_attention_tail": 0,
          "self_attention_work": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 80665.33333333334,
        "unexplained_share": 0.11286421464330122
      },
      {
        "calls": 3,
        "instructions_per_call": 740796.0,
        "state": {
          "cross_attention_work": 1026,
          "self_attention_tail": 0,
          "self_attention_work": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 105283.99999999999,
        "unexplained_share": 0.14212279763929608
      },
      {
        "calls": 3,
        "instructions_per_call": 755290.0,
        "state": {
          "cross_attention_work": 1218,
          "self_attention_tail": 0,
          "self_attention_work": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 116302.0,
        "unexplained_share": 0.15398323822637663
      },
      {
        "calls": 3,
        "instructions_per_call": 744744.0,
        "state": {
          "cross_attention_work": 1280,
          "self_attention_tail": 0,
          "self_attention_work": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 107269.66666666667,
        "unexplained_share": 0.14403562387433355
      },
      {
        "calls": 3,
        "instructions_per_call": 881778.3333333334,
        "state": {
          "cross_attention_work": 2256,
          "self_attention_tail": 0,
          "self_attention_work": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 226642.0,
        "unexplained_share": 0.2570283158843776
      },
      {
        "calls": 3,
        "instructions_per_call": 1099423.6666666667,
        "state": {
          "cross_attention_work": 0,
          "self_attention_tail": 9,
          "self_attention_work": 657,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 118607.99999999999,
        "unexplained_share": 0.1078819781637106
      },
      {
        "calls": 3,
        "instructions_per_call": 1085584.6666666667,
        "state": {
          "cross_attention_work": 0,
          "self_attention_tail": 0,
          "self_attention_work": 1280,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 122377.66666666669,
        "unexplained_share": 0.11272973027744805
      },
      {
        "calls": 3,
        "instructions_per_call": 1124152.6666666667,
        "state": {
          "cross_attention_work": 0,
          "self_attention_tail": 2,
          "self_attention_work": 1476,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 152790.33333333334,
        "unexplained_share": 0.135915999546918
      },
      {
        "calls": 3,
        "instructions_per_call": 1266836.0,
        "state": {
          "cross_attention_work": 0,
          "self_attention_tail": 11,
          "self_attention_work": 2457,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 285144.00000000006,
        "unexplained_share": 0.22508359408794829
      },
      {
        "calls": 3,
        "instructions_per_call": 1206477.0,
        "state": {
          "cross_attention_work": 0,
          "self_attention_tail": 0,
          "self_attention_work": 3072,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 223637.3333333333,
        "unexplained_share": 0.1853639425644528
      },
      {
        "calls": 3,
        "instructions_per_call": 1350076.6666666667,
        "state": {
          "cross_attention_work": 0,
          "self_attention_tail": 0,
          "self_attention_work": 5376,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 337397.3333333334,
        "unexplained_share": 0.2499097582112621
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 3,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 25.702831588437757,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 25.702831588437757,
      "iteration": 3,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}