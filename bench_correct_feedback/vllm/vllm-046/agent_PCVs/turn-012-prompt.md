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

This is iteration 10. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The quadratic request-count term added little explanatory power. Pending tokens times maximum context length tests attention and padding costs omitted by the successful request-count and token-count features.",
    "iteration": 9,
    "pcvs": [
      {
        "expression": "len(self.engine_core.engine_core.scheduler.requests)",
        "name": "active_requests",
        "rationale": "Explains shared per-request work."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests))",
        "name": "pending_tokens",
        "rationale": "Explains the dominant token-processing cost."
      },
      {
        "expression": "sum((max(0, self.engine_core.engine_core.scheduler.requests[k].num_tokens - self.engine_core.engine_core.scheduler.requests[k].num_computed_tokens) for k in self.engine_core.engine_core.scheduler.requests)) * max((self.engine_core.engine_core.scheduler.requests[k].num_tokens for k in self.engine_core.engine_core.scheduler.requests), default=0)",
        "name": "padded_attention_extent",
        "rationale": "Estimates attention work using pending query tokens and the batch's maximum context length, allowing for padded processing."
      },
      {
        "expression": "int(len(self.engine_core.engine_core.scheduler.waiting) == 2 and len(self.engine_core.engine_core.scheduler.running) == 0)",
        "name": "two_request_admission",
        "rationale": "Retains the workload-specific proxy for the costly first mixed-sampling admission."
      }
    ]
  },
  "case_id": "vllm-046",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-046",
    "distinct_states": 25,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "active_requests": 42798518.397052534,
        "padded_attention_extent": -43.01082199187569,
        "pending_tokens": 90130367.96625695,
        "two_request_admission": 16011536834.64672
      },
      "constant": 3836236.793880797,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 81.28955745697021,
    "max_unexplained_share": 0.22826116739652327,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "active_requests",
      "pending_tokens",
      "padded_attention_extent",
      "two_request_admission"
    ],
    "raw_files": [
      "run.2324671.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 176821719.0,
        "state": {
          "active_requests": 1,
          "padded_attention_extent": 13,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 40361532.0,
        "unexplained_share": 0.22826116739652327
      },
      {
        "calls": 1,
        "instructions_per_call": 145926754.0,
        "state": {
          "active_requests": 1,
          "padded_attention_extent": 24,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 9559297.0,
        "unexplained_share": 0.06550750111251018
      },
      {
        "calls": 1,
        "instructions_per_call": 145904522.0,
        "state": {
          "active_requests": 1,
          "padded_attention_extent": 25,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 9537523.0,
        "unexplained_share": 0.06536824814792237
      },
      {
        "calls": 1,
        "instructions_per_call": 150008958.0,
        "state": {
          "active_requests": 1,
          "padded_attention_extent": 48,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 13466108.0,
        "unexplained_share": 0.08976869234702636
      },
      {
        "calls": 1,
        "instructions_per_call": 149921576.0,
        "state": {
          "active_requests": 1,
          "padded_attention_extent": 49,
          "pending_tokens": 1,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 13407301.0,
        "unexplained_share": 0.08942876240842079
      },
      {
        "calls": 1,
        "instructions_per_call": 985606418.0,
        "state": {
          "active_requests": 1,
          "padded_attention_extent": 100,
          "pending_tokens": 10,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 37869444.0,
        "unexplained_share": 0.038422481132828826
      },
      {
        "calls": 1,
        "instructions_per_call": 327910013.0,
        "state": {
          "active_requests": 2,
          "padded_attention_extent": 24,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 58450546.0,
        "unexplained_share": 0.17825178763296867
      },
      {
        "calls": 2,
        "instructions_per_call": 311216874.0,
        "state": {
          "active_requests": 2,
          "padded_attention_extent": 46,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 41725690.5,
        "unexplained_share": 0.13407271258691456
      },
      {
        "calls": 1,
        "instructions_per_call": 327084951.0,
        "state": {
          "active_requests": 2,
          "padded_attention_extent": 48,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 57647772.0,
        "unexplained_share": 0.17624709367934205
      },
      {
        "calls": 2,
        "instructions_per_call": 315383657.0,
        "state": {
          "active_requests": 2,
          "padded_attention_extent": 96,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 45790654.5,
        "unexplained_share": 0.14519032132346668
      },
      {
        "calls": 1,
        "instructions_per_call": 334860756.0,
        "state": {
          "active_requests": 2,
          "padded_attention_extent": 98,
          "pending_tokens": 2,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 65172637.0,
        "unexplained_share": 0.1946260821318817
      },
      {
        "calls": 1,
        "instructions_per_call": 18868651619.0,
        "state": {
          "active_requests": 2,
          "padded_attention_extent": 220,
          "pending_tokens": 20,
          "two_request_admission": 1
        },
        "unexplained_instructions_per_call": 965152934.0,
        "unexplained_share": 0.05115113435175879
      },
      {
        "calls": 1,
        "instructions_per_call": 494177942.0,
        "state": {
          "active_requests": 3,
          "padded_attention_extent": 66,
          "pending_tokens": 3,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 91533257.0,
        "unexplained_share": 0.1852232753035343
      },
      {
        "calls": 2,
        "instructions_per_call": 465295181.0,
        "state": {
          "active_requests": 3,
          "padded_attention_extent": 141,
          "pending_tokens": 3,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 62733084.5,
        "unexplained_share": 0.13482427298124114
      },
      {
        "calls": 1,
        "instructions_per_call": 6335908433.0,
        "state": {
          "active_requests": 3,
          "padded_attention_extent": 1452,
          "pending_tokens": 66,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 255000102.0,
        "unexplained_share": 0.04024680986105406
      },
      {
        "calls": 1,
        "instructions_per_call": 652221060.0,
        "state": {
          "active_requests": 4,
          "padded_attention_extent": 192,
          "pending_tokens": 4,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 116633123.0,
        "unexplained_share": 0.17882452768391136
      },
      {
        "calls": 1,
        "instructions_per_call": 653466114.0,
        "state": {
          "active_requests": 4,
          "padded_attention_extent": 196,
          "pending_tokens": 4,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 117868159.0,
        "unexplained_share": 0.18037378905312296
      },
      {
        "calls": 1,
        "instructions_per_call": 8071532511.0,
        "state": {
          "active_requests": 4,
          "padded_attention_extent": 1764,
          "pending_tokens": 84,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 325401575.0,
        "unexplained_share": 0.04031472022896991
      },
      {
        "calls": 1,
        "instructions_per_call": 813806298.0,
        "state": {
          "active_requests": 5,
          "padded_attention_extent": 230,
          "pending_tokens": 5,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 145249240.0,
        "unexplained_share": 0.1784813417602723
      },
      {
        "calls": 1,
        "instructions_per_call": 813440454.0,
        "state": {
          "active_requests": 5,
          "padded_attention_extent": 235,
          "pending_tokens": 5,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 144873290.0,
        "unexplained_share": 0.1780994408227452
      },
      {
        "calls": 1,
        "instructions_per_call": 21685648320.0,
        "state": {
          "active_requests": 5,
          "padded_attention_extent": 10580,
          "pending_tokens": 230,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 737946774.0,
        "unexplained_share": 0.03402926964002338
      },
      {
        "calls": 1,
        "instructions_per_call": 972497810.0,
        "state": {
          "active_requests": 6,
          "padded_attention_extent": 288,
          "pending_tokens": 6,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 170986365.0,
        "unexplained_share": 0.17582185095100625
      },
      {
        "calls": 1,
        "instructions_per_call": 25464012961.0,
        "state": {
          "active_requests": 6,
          "padded_attention_extent": 12150,
          "pending_tokens": 270,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 868314918.0,
        "unexplained_share": 0.03409968881691538
      },
      {
        "calls": 1,
        "instructions_per_call": 30354168949.0,
        "state": {
          "active_requests": 7,
          "padded_attention_extent": 14812,
          "pending_tokens": 322,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1028870449.0,
        "unexplained_share": 0.033895523568069734
      },
      {
        "calls": 1,
        "instructions_per_call": 34689847754.0,
        "state": {
          "active_requests": 8,
          "padded_attention_extent": 17296,
          "pending_tokens": 368,
          "two_request_admission": 0
        },
        "unexplained_instructions_per_call": 1175765362.0,
        "unexplained_share": 0.03389364434049513
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a",
  "iteration": 9,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 22.826116739652328,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 22.826116739652328,
      "iteration": 9,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "dfef55f0f21210de71ec794366ba638d7970a0b8d018046c1e519fb63d4d117a"
  }
}