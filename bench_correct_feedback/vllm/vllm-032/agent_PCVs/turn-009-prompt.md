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

This is iteration 9. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The first two admission states may share fixed initialization paths whose execution counts are equal even though their total excess costs differ. A binary small-admission feature preserves that shared behavior while retaining separate admission and decode costs.",
    "iteration": 8,
    "pcvs": [
      {
        "expression": "len(self.running)",
        "name": "running_requests",
        "rationale": "Captures per-request decode scheduling work."
      },
      {
        "expression": "len(self.waiting) + len(self.skipped_waiting)",
        "name": "waiting_requests",
        "rationale": "Captures per-request admission work."
      },
      {
        "expression": "int(bool(self.waiting or self.skipped_waiting))",
        "name": "has_waiting_requests",
        "rationale": "Captures fixed work specific to admission steps."
      },
      {
        "expression": "int(0 < len(self.waiting) + len(self.skipped_waiting) <= 2)",
        "name": "small_admission",
        "rationale": "Identifies overhead shared by singleton and pair admissions, without imposing the unsuccessful three-to-two weighting."
      }
    ]
  },
  "case_id": "vllm-032",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 28,
    "case": "vllm-032",
    "distinct_states": 14,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "has_waiting_requests": -767.7055555555451,
        "running_requests": 43414.62448979589,
        "small_admission": 8128.166666666659,
        "waiting_requests": 97864.11111111108
      },
      "constant": 55036.73344671206,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 128.5167082590051,
    "max_unexplained_share": 0.5712307700168094,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "running_requests",
      "waiting_requests",
      "has_waiting_requests",
      "small_admission"
    ],
    "raw_files": [
      "run.2264236.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 391446.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 1,
          "waiting_requests": 1
        },
        "unexplained_instructions_per_call": 223606.0,
        "unexplained_share": 0.5712307700168094
      },
      {
        "calls": 1,
        "instructions_per_call": 484263.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 1,
          "waiting_requests": 2
        },
        "unexplained_instructions_per_call": 225700.0,
        "unexplained_share": 0.466069057516267
      },
      {
        "calls": 1,
        "instructions_per_call": 523324.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 0,
          "waiting_requests": 3
        },
        "unexplained_instructions_per_call": 181267.0,
        "unexplained_share": 0.3463762411049369
      },
      {
        "calls": 1,
        "instructions_per_call": 661357.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 0,
          "waiting_requests": 4
        },
        "unexplained_instructions_per_call": 222788.0,
        "unexplained_share": 0.33686496098173907
      },
      {
        "calls": 1,
        "instructions_per_call": 815101.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 0,
          "waiting_requests": 5
        },
        "unexplained_instructions_per_call": 275483.0,
        "unexplained_share": 0.33797406701746163
      },
      {
        "calls": 1,
        "instructions_per_call": 961120.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 0,
          "waiting_requests": 6
        },
        "unexplained_instructions_per_call": 322355.0,
        "unexplained_share": 0.33539516397536207
      },
      {
        "calls": 1,
        "instructions_per_call": 1111726.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 0,
          "waiting_requests": 7
        },
        "unexplained_instructions_per_call": 373449.0,
        "unexplained_share": 0.3359182028665337
      },
      {
        "calls": 1,
        "instructions_per_call": 1258973.0,
        "state": {
          "has_waiting_requests": 1,
          "running_requests": 0,
          "small_admission": 0,
          "waiting_requests": 8
        },
        "unexplained_instructions_per_call": 421489.0,
        "unexplained_share": 0.3347879581214212
      },
      {
        "calls": 5,
        "instructions_per_call": 146464.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 1,
          "small_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 52009.0,
        "unexplained_share": 0.35509749836137205
      },
      {
        "calls": 7,
        "instructions_per_call": 221659.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 2,
          "small_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 81040.42857142854,
        "unexplained_share": 0.3656085634755572
      },
      {
        "calls": 3,
        "instructions_per_call": 286876.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 3,
          "small_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 101446.0,
        "unexplained_share": 0.3536231681981065
      },
      {
        "calls": 2,
        "instructions_per_call": 358818.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 4,
          "small_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 127474.0,
        "unexplained_share": 0.35526088434805386
      },
      {
        "calls": 2,
        "instructions_per_call": 429736.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 5,
          "small_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 151588.5,
        "unexplained_share": 0.3527479661931977
      },
      {
        "calls": 1,
        "instructions_per_call": 500122.0,
        "state": {
          "has_waiting_requests": 0,
          "running_requests": 6,
          "small_admission": 0,
          "waiting_requests": 0
        },
        "unexplained_instructions_per_call": 175846.0,
        "unexplained_share": 0.3516062080852272
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251",
  "iteration": 8,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 57.12307700168095,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 57.12307700168095,
      "iteration": 8,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "6a0c7537f99a70cc7bdb701ff6957e5f8fe2e5f9cd35c0635fe9301617c26251"
  }
}