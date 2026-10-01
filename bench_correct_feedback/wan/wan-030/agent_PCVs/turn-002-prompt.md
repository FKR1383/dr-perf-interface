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
    "hypothesis": "Instruction count is approximately fixed dispatch and allocation overhead plus a linear term in tensor elements. The fixture uses a constant tensor shape, so counts should be nearly constant across entries.",
    "iteration": 1,
    "pcvs": [
      {
        "expression": "noise_pred.numel()",
        "name": "noise_elements",
        "rationale": "The region performs subtraction, scalar multiplication, and addition over the noise tensor; its element count captures the arithmetic work."
      }
    ]
  },
  "case_id": "wan-030",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 39,
    "case": "wan-030",
    "distinct_states": 1,
    "dropped_calls": 0,
    "gate_pass": false,
    "gate_reasons": [
      "insufficient state points: 1; need 3"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 14.425246494822204,
    "max_unexplained_share": null,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "noise_elements"
    ],
    "raw_files": [
      "run.1579072.json"
    ],
    "required_states": 3,
    "returncode": 0,
    "states": [
      {
        "calls": 39,
        "instructions_per_call": 47651.307692307695,
        "state": {
          "noise_elements": 512
        }
      }
    ],
    "sufficient_points": false,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "c130dcedd92a3b272e4f896320f2a09cb12ec4516ca9d67ef9acf4383abc38ce",
  "iteration": 1,
  "script_decision": {
    "assessment": {
      "irregularity_percent": null,
      "reasons": [
        "insufficient state points: 1; need 3",
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
        "insufficient state points: 1; need 3",
        "Dr. Perf did not produce an irregularity value"
      ],
      "status": "invalid",
      "threshold_percent": 10.0
    },
    "workload_digest": "c130dcedd92a3b272e4f896320f2a09cb12ec4516ca9d67ef9acf4383abc38ce"
  }
}