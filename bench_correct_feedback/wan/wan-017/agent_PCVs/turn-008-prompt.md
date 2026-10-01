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

This is iteration 8. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The best previous remainder model combined query and context lengths, obscuring query-row costs. Using query size directly alongside attention tails and both rotary terms should explain more of the cross-attention residual while preserving self-attention scaling.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim",
        "name": "query_elements",
        "rationale": "Exposes query-row work directly, including output projection and attention row overhead."
      },
      {
        "expression": "hidden_states.shape[0] * attn.heads * hidden_states.shape[1] * ((hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]) % 16)",
        "name": "attention_tail_elements",
        "rationale": "Captures attention remainder work, which was absent from the previous candidate and matters especially for short cross-attention contexts."
      },
      {
        "expression": "hidden_states.shape[0] * hidden_states.shape[1] * attn.inner_dim if rotary_emb is not None else 0",
        "name": "rotary_elements",
        "rationale": "Captures additional elementwise work on the rotary path."
      },
      {
        "expression": "int(rotary_emb is not None)",
        "name": "uses_rotary",
        "rationale": "Captures fixed rotary dispatch and allocation overhead."
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
        "attention_tail_elements": 40.64810886428087,
        "query_elements": 36.14775368301577,
        "rotary_elements": 126.03502342521845,
        "uses_rotary": 321065.2978677142
      },
      "constant": 633449.1790798882,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 20.653687010984868,
    "max_unexplained_share": 0.135850128655484,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "query_elements",
      "attention_tail_elements",
      "rotary_elements",
      "uses_rotary"
    ],
    "raw_files": [
      "run.1562070.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 681374.0,
        "state": {
          "attention_tail_elements": 144,
          "query_elements": 288,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 37643.66666666667,
        "unexplained_share": 0.05524670249623066
      },
      {
        "calls": 3,
        "instructions_per_call": 1099576.0,
        "state": {
          "attention_tail_elements": 324,
          "query_elements": 288,
          "rotary_elements": 288,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 66267.33333333333,
        "unexplained_share": 0.06026626020696462
      },
      {
        "calls": 3,
        "instructions_per_call": 1087005.3333333333,
        "state": {
          "attention_tail_elements": 0,
          "query_elements": 512,
          "rotary_elements": 512,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 54125.99999999999,
        "unexplained_share": 0.049793683931633574
      },
      {
        "calls": 3,
        "instructions_per_call": 713656.3333333334,
        "state": {
          "attention_tail_elements": 384,
          "query_elements": 512,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 51340.99999999999,
        "unexplained_share": 0.07194078942759095
      },
      {
        "calls": 3,
        "instructions_per_call": 1123827.0,
        "state": {
          "attention_tail_elements": 144,
          "query_elements": 576,
          "rotary_elements": 576,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 69561.66666666667,
        "unexplained_share": 0.06189713066750191
      },
      {
        "calls": 3,
        "instructions_per_call": 741639.3333333334,
        "state": {
          "attention_tail_elements": 648,
          "query_elements": 576,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 64378.0,
        "unexplained_share": 0.08680499685831118
      },
      {
        "calls": 3,
        "instructions_per_call": 754685.3333333334,
        "state": {
          "attention_tail_elements": 648,
          "query_elements": 864,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 68326.33333333334,
        "unexplained_share": 0.09053618815082314
      },
      {
        "calls": 3,
        "instructions_per_call": 1267761.6666666667,
        "state": {
          "attention_tail_elements": 1188,
          "query_elements": 864,
          "rotary_elements": 864,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 123633.33333333334,
        "unexplained_share": 0.09752095885530535
      },
      {
        "calls": 3,
        "instructions_per_call": 1207045.6666666667,
        "state": {
          "attention_tail_elements": 0,
          "query_elements": 1024,
          "rotary_elements": 1024,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 88144.66666666667,
        "unexplained_share": 0.07302512995227742
      },
      {
        "calls": 3,
        "instructions_per_call": 745294.0,
        "state": {
          "attention_tail_elements": 512,
          "query_elements": 1024,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 61133.333333333336,
        "unexplained_share": 0.08202579563680015
      },
      {
        "calls": 3,
        "instructions_per_call": 1349469.0,
        "state": {
          "attention_tail_elements": 0,
          "query_elements": 1536,
          "rotary_elements": 1536,
          "uses_rotary": 1
        },
        "unexplained_instructions_per_call": 135960.99999999997,
        "unexplained_share": 0.10075148076762043
      },
      {
        "calls": 3,
        "instructions_per_call": 881164.6666666666,
        "state": {
          "attention_tail_elements": 1728,
          "query_elements": 1536,
          "rotary_elements": 0,
          "uses_rotary": 0
        },
        "unexplained_instructions_per_call": 119706.33333333333,
        "unexplained_share": 0.135850128655484
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 13.585012865548398,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 13.585012865548398,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "5a88fdf3afe1d4609b190ce3d06e2b77ab3447299d9e116d33fc29528ab44145"
  }
}