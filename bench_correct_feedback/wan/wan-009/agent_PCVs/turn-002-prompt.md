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
    "hypothesis": "Instruction count is dominated by fixed attribute-assignment overhead, new cache-list construction, and disposal of previous cache lists. The varying index values should not materially affect reset cost.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "self._cached_conv_counts['decoder'] + self._cached_conv_counts['encoder']",
        "name": "cache_slots",
        "rationale": "Captures the work of allocating and filling the two feature-cache lists."
      },
      {
        "expression": "len(self.__dict__.get('_feat_map', ())) + len(self.__dict__.get('_enc_feat_map', ()))",
        "name": "existing_cache_slots",
        "rationale": "Captures disposal of existing cache lists and distinguishes initial cache creation from subsequent resets."
      }
    ]
  },
  "case_id": "wan-009",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 18,
    "case": "wan-009",
    "distinct_states": 2,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 2; need 4"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 10.665980961173773,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "cache_slots",
      "existing_cache_slots"
    ],
    "raw_files": [
      "run.1541560.json"
    ],
    "required_states": 4,
    "returncode": 0,
    "states": [
      {
        "calls": 3,
        "instructions_per_call": 92561.66666666667,
        "state": {
          "cache_slots": 43,
          "existing_cache_slots": 0
        }
      },
      {
        "calls": 15,
        "instructions_per_call": 92258.33333333333,
        "state": {
          "cache_slots": 43,
          "existing_cache_slots": 43
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "00e880d4388f88685d791b292ee8af2972bd74e76763acdabe15410a0c7c3290",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 2; need 4",
        "Dr. Perf did not produce an irregularity value"
      ],
      "success": false,
      "threshold_percent": 10.0,
      "valid": false
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": null,
      "iteration": 1,
      "reasons": [
        "insufficient state points: 2; need 4",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "00e880d4388f88685d791b292ee8af2972bd74e76763acdabe15410a0c7c3290"
  }
}