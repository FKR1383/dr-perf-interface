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
    "hypothesis": "Pending token count and attention interactions explain model execution costs, while active and waiting request counts explain scheduling and output overhead. Prefix-cache hits may reduce pending-token estimation accuracy.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests)",
        "name": "active_requests",
        "rationale": "Captures per-request scheduling, sampling, and output processing costs."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "pending_tokens",
        "rationale": "Estimates token positions requiring model execution, distinguishing prefill from decoding."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) * (self.engine_core.engine_core.scheduler.requests[k].num_tokens + self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens + 1) // 2 for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "attention_work",
        "rationale": "Estimates causal attention interactions for pending tokens."
      },
      {
        "expression": "len(self.engine_core.engine_core.scheduler.waiting)",
        "name": "waiting_requests",
        "rationale": "Captures admission, prefix-cache lookup, and prefill setup costs."
      }
    ]
  },
  "case_id": "vllm-046",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-046",
    "distinct_states": 24,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_requests": 42800437.23935467,
        "attention_work": 2450.025549061427,
        "pending_tokens": 90041828.6492319,
        "waiting_requests": 1242170.360244763
      },
      "constant": 720158.8946045921,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 81.62403655564412,
    "max_unexplained_share": 0.8997943941339906,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "active_requests",
      "pending_tokens",
      "attention_work",
      "waiting_requests"
    ],
    "raw_files": [
      "run.2318804.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 176844241.0,
        "state": {
          "active_requests": 1,
          "attention_work": 13,
          "pending_tokens": 1,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 43288448.0,
        "unexplained_share": 0.24478291040305916
      },
      {
        "calls": 1,
        "instructions_per_call": 145977406.0,
        "state": {
          "active_requests": 1,
          "attention_work": 24,
          "pending_tokens": 1,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 12469359.0,
        "unexplained_share": 0.0854197874977995
      },
      {
        "calls": 1,
        "instructions_per_call": 145940525.0,
        "state": {
          "active_requests": 1,
          "attention_work": 25,
          "pending_tokens": 1,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 12433296.0,
        "unexplained_share": 0.08519426663704273
      },
      {
        "calls": 1,
        "instructions_per_call": 150035923.0,
        "state": {
          "active_requests": 1,
          "attention_work": 48,
          "pending_tokens": 1,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 16427311.0,
        "unexplained_share": 0.10948918546660322
      },
      {
        "calls": 1,
        "instructions_per_call": 149965434.0,
        "state": {
          "active_requests": 1,
          "attention_work": 49,
          "pending_tokens": 1,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 16367091.0,
        "unexplained_share": 0.10913909001190235
      },
      {
        "calls": 1,
        "instructions_per_call": 985577124.0,
        "state": {
          "active_requests": 1,
          "attention_work": 55,
          "pending_tokens": 10,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 40843157.0,
        "unexplained_share": 0.041440853288311506
      },
      {
        "calls": 1,
        "instructions_per_call": 327940802.0,
        "state": {
          "active_requests": 2,
          "attention_work": 22,
          "pending_tokens": 2,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 61470475.0,
        "unexplained_share": 0.1874438149358432
      },
      {
        "calls": 2,
        "instructions_per_call": 311242466.5,
        "state": {
          "active_requests": 2,
          "attention_work": 46,
          "pending_tokens": 2,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 44730431.0,
        "unexplained_share": 0.14371570660972127
      },
      {
        "calls": 1,
        "instructions_per_call": 327128746.0,
        "state": {
          "active_requests": 2,
          "attention_work": 48,
          "pending_tokens": 2,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 60664341.0,
        "unexplained_share": 0.18544484928878735
      },
      {
        "calls": 2,
        "instructions_per_call": 315416817.0,
        "state": {
          "active_requests": 2,
          "attention_work": 96,
          "pending_tokens": 2,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 48853444.0,
        "unexplained_share": 0.15488534969268933
      },
      {
        "calls": 1,
        "instructions_per_call": 334926415.0,
        "state": {
          "active_requests": 2,
          "attention_work": 98,
          "pending_tokens": 2,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 68329879.0,
        "unexplained_share": 0.20401460123711054
      },
      {
        "calls": 1,
        "instructions_per_call": 18864213241.0,
        "state": {
          "active_requests": 2,
          "attention_work": 111,
          "pending_tokens": 20,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 16973913324.0,
        "unexplained_share": 0.8997943941339906
      },
      {
        "calls": 1,
        "instructions_per_call": 494197351.0,
        "state": {
          "active_requests": 3,
          "attention_work": 66,
          "pending_tokens": 3,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 94675552.0,
        "unexplained_share": 0.19157438178983682
      },
      {
        "calls": 2,
        "instructions_per_call": 465341278.5,
        "state": {
          "active_requests": 3,
          "attention_work": 141,
          "pending_tokens": 3,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 65855063.5,
        "unexplained_share": 0.14151992643394948
      },
      {
        "calls": 1,
        "instructions_per_call": 6335937477.0,
        "state": {
          "active_requests": 3,
          "attention_work": 759,
          "pending_tokens": 66,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 258363804.0,
        "unexplained_share": 0.04077751791867942
      },
      {
        "calls": 2,
        "instructions_per_call": 652880208.0,
        "state": {
          "active_requests": 4,
          "attention_work": 192,
          "pending_tokens": 4,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 120451168.0,
        "unexplained_share": 0.1844919887661842
      },
      {
        "calls": 1,
        "instructions_per_call": 8071553977.0,
        "state": {
          "active_requests": 4,
          "attention_work": 924,
          "pending_tokens": 84,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 328906562.0,
        "unexplained_share": 0.040748852443683536
      },
      {
        "calls": 1,
        "instructions_per_call": 813853139.0,
        "state": {
          "active_requests": 5,
          "attention_work": 230,
          "pending_tokens": 5,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 148505137.0,
        "unexplained_share": 0.18247166458370076
      },
      {
        "calls": 1,
        "instructions_per_call": 813499160.0,
        "state": {
          "active_requests": 5,
          "attention_work": 235,
          "pending_tokens": 5,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 148140701.0,
        "unexplained_share": 0.18210307801670012
      },
      {
        "calls": 1,
        "instructions_per_call": 21685709218.0,
        "state": {
          "active_requests": 5,
          "attention_work": 5405,
          "pending_tokens": 230,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 741674666.0,
        "unexplained_share": 0.034201079547095496
      },
      {
        "calls": 1,
        "instructions_per_call": 972550824.0,
        "state": {
          "active_requests": 6,
          "attention_work": 280,
          "pending_tokens": 6,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 174290235.0,
        "unexplained_share": 0.17920938494829758
      },
      {
        "calls": 1,
        "instructions_per_call": 25464021952.0,
        "state": {
          "active_requests": 6,
          "attention_work": 6210,
          "pending_tokens": 270,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 872096673.0,
        "unexplained_share": 0.03424819043291406
      },
      {
        "calls": 1,
        "instructions_per_call": 30354222911.0,
        "state": {
          "active_requests": 7,
          "attention_work": 7567,
          "pending_tokens": 322,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 1032884818.0,
        "unexplained_share": 0.03402771406892763
      },
      {
        "calls": 1,
        "instructions_per_call": 34689897632.0,
        "state": {
          "active_requests": 8,
          "attention_work": 8652,
          "pending_tokens": 368,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 1179907495.0,
        "unexplained_share": 0.03401300019725582
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 89.97943941339906,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 89.97943941339906,
      "iteration": 1,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}