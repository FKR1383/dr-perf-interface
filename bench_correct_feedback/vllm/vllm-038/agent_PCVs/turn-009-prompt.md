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
    "hypothesis": "Prompt-length feedback isolated three elevated observations: singleton short prefill, paired short prefill, and paired short decode. A shared piecewise entry-state predictor tests their excess cost alongside the main workload dimensions.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "len(scheduler_output.num_scheduled_tokens)",
        "name": "scheduled_requests",
        "rationale": "Captures per-request processing."
      },
      {
        "expression": "len([r for r in self.running if r.num_output_tokens + 1 >= r.max_tokens])",
        "name": "finishing_requests",
        "rationale": "Captures request completion and resource release."
      },
      {
        "expression": "len(scheduler_output.scheduled_new_reqs)",
        "name": "new_requests",
        "rationale": "Captures prefill completion work."
      },
      {
        "expression": "(2 if len(scheduler_output.scheduled_new_reqs) == 1 else 1) if self.running and max((r.num_prompt_tokens for r in self.running)) < 20 and (scheduler_output.scheduled_new_reqs or len(scheduler_output.num_scheduled_tokens) == 2) else 0",
        "name": "short_batch_regime",
        "rationale": "Separates the short-prompt prefill and two-request decode observations with consistently elevated costs, while excluding the ordinary short-prompt singleton decode."
      }
    ]
  },
  "case_id": "vllm-038",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-038",
    "distinct_states": 19,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "finishing_requests": 13634.601029762212,
        "new_requests": 13636.13111101515,
        "scheduled_requests": 15996.208667786872,
        "short_batch_regime": 5414.488183449219
      },
      "constant": 32351.857163828157,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 99.55535038514063,
    "max_unexplained_share": 0.46711430337287657,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "scheduled_requests",
      "finishing_requests",
      "new_requests",
      "short_batch_regime"
    ],
    "raw_files": [
      "run.2283175.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 5,
        "instructions_per_call": 70184.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 1,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 16345.199999999999,
        "unexplained_share": 0.23289068733614499
      },
      {
        "calls": 1,
        "instructions_per_call": 166653.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 1,
          "scheduled_requests": 1,
          "short_batch_regime": 2
        },
        "unexplained_instructions_per_call": 77846.0,
        "unexplained_share": 0.46711430337287657
      },
      {
        "calls": 1,
        "instructions_per_call": 60851.0,
        "state": {
          "finishing_requests": 0,
          "new_requests": 0,
          "scheduled_requests": 2,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 13485.0,
        "unexplained_share": 0.2216068758114082
      },
      {
        "calls": 1,
        "instructions_per_call": 147074.0,
        "state": {
          "finishing_requests": 0,
          "new_requests": 2,
          "scheduled_requests": 2,
          "short_batch_regime": 1
        },
        "unexplained_instructions_per_call": 58975.0,
        "unexplained_share": 0.40098861797462504
      },
      {
        "calls": 3,
        "instructions_per_call": 93851.33333333333,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 2,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 21819.333333333332,
        "unexplained_share": 0.23248826157682007
      },
      {
        "calls": 1,
        "instructions_per_call": 129079.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 2,
          "short_batch_regime": 1
        },
        "unexplained_instructions_per_call": 48660.0,
        "unexplained_share": 0.3769784395602693
      },
      {
        "calls": 2,
        "instructions_per_call": 111739.5,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 2,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 25190.5,
        "unexplained_share": 0.225439526756429
      },
      {
        "calls": 2,
        "instructions_per_call": 115416.5,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 3,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 25694.0,
        "unexplained_share": 0.22261981605749612
      },
      {
        "calls": 1,
        "instructions_per_call": 173408.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 3,
          "scheduled_requests": 3,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 38818.0,
        "unexplained_share": 0.22385357076951468
      },
      {
        "calls": 1,
        "instructions_per_call": 132820.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 3,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 29058.0,
        "unexplained_share": 0.2187772925764192
      },
      {
        "calls": 1,
        "instructions_per_call": 213944.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 4,
          "scheduled_requests": 4,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 45507.0,
        "unexplained_share": 0.2127051938825113
      },
      {
        "calls": 2,
        "instructions_per_call": 155462.5,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 4,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 34115.0,
        "unexplained_share": 0.21944198761759268
      },
      {
        "calls": 1,
        "instructions_per_call": 164488.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 0,
          "scheduled_requests": 5,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 37242.0,
        "unexplained_share": 0.2264116531297116
      },
      {
        "calls": 1,
        "instructions_per_call": 177416.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 5,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 38221.0,
        "unexplained_share": 0.2154315281598052
      },
      {
        "calls": 1,
        "instructions_per_call": 275461.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 5,
          "scheduled_requests": 5,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 59291.0,
        "unexplained_share": 0.21524281114204916
      },
      {
        "calls": 1,
        "instructions_per_call": 297020.0,
        "state": {
          "finishing_requests": 1,
          "new_requests": 6,
          "scheduled_requests": 6,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 61906.0,
        "unexplained_share": 0.208423675173389
      },
      {
        "calls": 1,
        "instructions_per_call": 199488.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 0,
          "scheduled_requests": 6,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 42819.0,
        "unexplained_share": 0.21464448989412896
      },
      {
        "calls": 1,
        "instructions_per_call": 353324.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 7,
          "scheduled_requests": 7,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 72550.0,
        "unexplained_share": 0.2053356126388244
      },
      {
        "calls": 1,
        "instructions_per_call": 394401.0,
        "state": {
          "finishing_requests": 2,
          "new_requests": 8,
          "scheduled_requests": 8,
          "short_batch_regime": 0
        },
        "unexplained_instructions_per_call": 80699.0,
        "unexplained_share": 0.2046115501735543
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 46.71143033728766,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 46.71143033728766,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "e8366b64069aef3ad064cf968312fc6f336a6a87766f55d9ce3bbe751715ad89"
  }
}