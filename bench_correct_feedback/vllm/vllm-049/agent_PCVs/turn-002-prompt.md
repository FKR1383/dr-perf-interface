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
    "hypothesis": "Instruction count is approximately a fixed constructor cost plus a linear term in prompt length.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(prompt_token_ids) if prompt_token_ids is not None else int(prompt_embeds.shape[0]) if prompt_embeds is not None else 0",
        "name": "prompt_length",
        "rationale": "Captures the length-dependent cost of copying prompt token IDs or allocating placeholder IDs; the exercised constructor otherwise follows a fixed path."
      }
    ]
  },
  "case_id": "vllm-049",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 12,
    "case": "vllm-049",
    "distinct_states": 12,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "prompt_length": 0.6573426573426584
      },
      "constant": 18859.477272727283,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 11.760320946574211,
    "max_unexplained_share": 0.5762924681091114,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "prompt_length"
    ],
    "raw_files": [
      "run.2336542.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 54953.0,
        "state": {
          "prompt_length": 1
        },
        "unexplained_instructions_per_call": 31669.0,
        "unexplained_share": 0.5762924681091114
      },
      {
        "calls": 1,
        "instructions_per_call": 40917.0,
        "state": {
          "prompt_length": 2
        },
        "unexplained_instructions_per_call": 20118.0,
        "unexplained_share": 0.4916782755333969
      },
      {
        "calls": 1,
        "instructions_per_call": 24827.0,
        "state": {
          "prompt_length": 3
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.2743787006082088
      },
      {
        "calls": 1,
        "instructions_per_call": 24973.0,
        "state": {
          "prompt_length": 4
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.27277459656428943
      },
      {
        "calls": 1,
        "instructions_per_call": 30173.0,
        "state": {
          "prompt_length": 5
        },
        "unexplained_instructions_per_call": 11561.0,
        "unexplained_share": 0.38315712723295664
      },
      {
        "calls": 1,
        "instructions_per_call": 24982.0,
        "state": {
          "prompt_length": 6
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.2726763269554079
      },
      {
        "calls": 1,
        "instructions_per_call": 24865.0,
        "state": {
          "prompt_length": 7
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.27395938065553993
      },
      {
        "calls": 1,
        "instructions_per_call": 25000.0,
        "state": {
          "prompt_length": 8
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.27248
      },
      {
        "calls": 1,
        "instructions_per_call": 24859.0,
        "state": {
          "prompt_length": 9
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.274025503841667
      },
      {
        "calls": 1,
        "instructions_per_call": 25002.0,
        "state": {
          "prompt_length": 10
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.2724582033437325
      },
      {
        "calls": 1,
        "instructions_per_call": 24872.0,
        "state": {
          "prompt_length": 11
        },
        "unexplained_instructions_per_call": 6812.0,
        "unexplained_share": 0.273882277259569
      },
      {
        "calls": 1,
        "instructions_per_call": 30347.0,
        "state": {
          "prompt_length": 12
        },
        "unexplained_instructions_per_call": 11561.0,
        "unexplained_share": 0.3809602267110423
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "77909abfee49a2c509c2a876ef1995b97c58d79af5ee9c2aa6047d68a89ac552",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 57.62924681091114,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 57.62924681091114,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "77909abfee49a2c509c2a876ef1995b97c58d79af5ee9c2aa6047d68a89ac552"
  }
}