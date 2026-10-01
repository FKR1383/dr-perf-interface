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
    "hypothesis": "The small-prefill correction left substantial unexplained work and did not distinguish repeated decode states. Aggregate prompt length tests whether request sequence size explains those differences and costs in token bookkeeping or cache-related helpers.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "len(scheduler_output.num_scheduled_tokens)",
        "name": "scheduled_requests",
        "rationale": "Captures per-request processing."
      },
      {
        "expression": "len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens])",
        "name": "finishing_requests",
        "rationale": "Captures completion and resource release."
      },
      {
        "expression": "len(scheduler_output.scheduled_new_reqs)",
        "name": "new_requests",
        "rationale": "Captures prefill completion work."
      },
      {
        "expression": "sum((r.num_prompt_tokens for r in self.running))",
        "name": "prompt_tokens",
        "rationale": "Distinguishes requests with different prompt histories, including observations previously grouped under identical batch and completion counts."
      }
    ]
  },
  "case_id": "vllm-038",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-038",
    "distinct_states": 27,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "finishing_requests": 10484.335318257145,
        "new_requests": 11145.223647706474,
        "prompt_tokens": -3.284444274623579,
        "scheduled_requests": 13469.548935496461
      },
      "constant": 26178.157245467417,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 133.47910998621956,
    "max_unexplained_share": 0.6252695711608942,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "scheduled_requests",
      "finishing_requests",
      "new_requests",
      "prompt_tokens"
    ],
    "raw_files": [
      "run.2282334.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 70661.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 11,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 26091.0,
        "unexplained_share": 0.36924187316907486
      },
      {
        "calls": 1,
        "instructions_per_call": 71834.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 21,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 27218.0,
        "unexplained_share": 0.3789013559038895
      },
      {
        "calls": 1,
        "instructions_per_call": 69919.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 22,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 25471.0,
        "unexplained_share": 0.3642929675767674
      },
      {
        "calls": 1,
        "instructions_per_call": 70198.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 45,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 25795.0,
        "unexplained_share": 0.36746061141343056
      },
      {
        "calls": 1,
        "instructions_per_call": 69636.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 46,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 25158.0,
        "unexplained_share": 0.36127864897466827
      },
      {
        "calls": 1,
        "instructions_per_call": 169714.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 1,
          "prompt_tokens": 10,
          "scheduled_requests": 1
        },
        "unexplained_instructions_per_call": 106117.0,
        "unexplained_share": 0.6252695711608942
      },
      {
        "calls": 1,
        "instructions_per_call": 60494.0,
        "state": {
          "finishing_requests": 0,
          "new_requests": 0,
          "prompt_tokens": 44,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 21120.0,
        "unexplained_share": 0.3491255331107217
      },
      {
        "calls": 1,
        "instructions_per_call": 148040.0,
        "state": {
          "finishing_requests": 0,
          "new_requests": 2,
          "prompt_tokens": 20,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 76943.0,
        "unexplained_share": 0.5197446636044313
      },
      {
        "calls": 1,
        "instructions_per_call": 130008.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 20,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 64872.0,
        "unexplained_share": 0.4989846778659775
      },
      {
        "calls": 1,
        "instructions_per_call": 91729.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 42,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 33009.0,
        "unexplained_share": 0.35985348145079527
      },
      {
        "calls": 1,
        "instructions_per_call": 96195.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 44,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 35891.0,
        "unexplained_share": 0.37310671032797965
      },
      {
        "calls": 1,
        "instructions_per_call": 93001.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 92,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 33270.0,
        "unexplained_share": 0.35773808883775443
      },
      {
        "calls": 1,
        "instructions_per_call": 110924.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "prompt_tokens": 90,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 40021.0,
        "unexplained_share": 0.36079658144315024
      },
      {
        "calls": 1,
        "instructions_per_call": 112196.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "prompt_tokens": 92,
          "scheduled_requests": 2
        },
        "unexplained_instructions_per_call": 41170.0,
        "unexplained_share": 0.36694712823986597
      },
      {
        "calls": 1,
        "instructions_per_call": 115315.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 63,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 41131.0,
        "unexplained_share": 0.3566838659324459
      },
      {
        "calls": 1,
        "instructions_per_call": 116161.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 138,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 40999.0,
        "unexplained_share": 0.3529497852119042
      },
      {
        "calls": 1,
        "instructions_per_call": 172024.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 3,
          "prompt_tokens": 66,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 60917.0,
        "unexplained_share": 0.3541191926707901
      },
      {
        "calls": 1,
        "instructions_per_call": 132908.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "prompt_tokens": 135,
          "scheduled_requests": 3
        },
        "unexplained_instructions_per_call": 47438.0,
        "unexplained_share": 0.35692358624010595
      },
      {
        "calls": 1,
        "instructions_per_call": 213398.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 4,
          "prompt_tokens": 84,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 73510.0,
        "unexplained_share": 0.34447370640774516
      },
      {
        "calls": 2,
        "instructions_per_call": 156009.5,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "prompt_tokens": 184,
          "scheduled_requests": 4
        },
        "unexplained_instructions_per_call": 55875.5,
        "unexplained_share": 0.35815447136232087
      },
      {
        "calls": 1,
        "instructions_per_call": 164841.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "prompt_tokens": 230,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 58682.0,
        "unexplained_share": 0.35599153123312766
      },
      {
        "calls": 1,
        "instructions_per_call": 177784.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "prompt_tokens": 225,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 62900.0,
        "unexplained_share": 0.35380011699590513
      },
      {
        "calls": 1,
        "instructions_per_call": 274838.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 5,
          "prompt_tokens": 230,
          "scheduled_requests": 5
        },
        "unexplained_instructions_per_call": 96243.0,
        "unexplained_share": 0.3501808338002751
      },
      {
        "calls": 1,
        "instructions_per_call": 297490.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 6,
          "prompt_tokens": 270,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 101676.0,
        "unexplained_share": 0.3417795556153148
      },
      {
        "calls": 1,
        "instructions_per_call": 198939.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "prompt_tokens": 274,
          "scheduled_requests": 6
        },
        "unexplained_instructions_per_call": 69557.0,
        "unexplained_share": 0.34963983934773973
      },
      {
        "calls": 1,
        "instructions_per_call": 353485.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 7,
          "prompt_tokens": 322,
          "scheduled_requests": 7
        },
        "unexplained_instructions_per_call": 120927.0,
        "unexplained_share": 0.3420993818691034
      },
      {
        "calls": 1,
        "instructions_per_call": 393016.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 8,
          "prompt_tokens": 368,
          "scheduled_requests": 8
        },
        "unexplained_instructions_per_call": 133279.0,
        "unexplained_share": 0.3391185091701101
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 62.52695711608942,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 62.52695711608942,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89"
  }
}