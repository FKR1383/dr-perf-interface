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

This is iteration 5. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "Separate request-count features for observed prompt-length regimes should explain branch-specific work better than a shared linear character-cost model, while keeping initialization independent.",
    "iteration": 4,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Isolates the initial default-options call and its initialization cost."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) if len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]) < 64 else 0",
        "name": "short_prompt_requests",
        "rationale": "Models per-request processing for batches of short prompts."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) if 64 <= len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]) < 128 else 0",
        "name": "medium_prompt_requests",
        "rationale": "Models per-request processing for batches of medium-length prompts."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else len(params) if len(prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]['prompt'] if 'prompt' in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0] else prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable[0]) >= 128 else 0",
        "name": "long_prompt_requests",
        "rationale": "Models the larger per-request tokenization and input-processing cost of long prompts."
      }
    ]
  },
  "case_id": "vllm-002",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 8,
    "case": "vllm-002",
    "distinct_states": 8,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "default_tokenization": 55072033.77448061,
        "long_prompt_requests": 1108226.586053413,
        "medium_prompt_requests": 823134.8635014815,
        "short_prompt_requests": 552983.0370919857
      },
      "constant": 605035.6086795343,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 120.07111619971693,
    "max_unexplained_share": 0.14257337181969026,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "short_prompt_requests",
      "medium_prompt_requests",
      "long_prompt_requests"
    ],
    "raw_files": [
      "run.1783442.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 6895932.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 5,
          "medium_prompt_requests": 0,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 840720.0,
        "unexplained_share": 0.1219153553138285
      },
      {
        "calls": 1,
        "instructions_per_call": 7925086.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 6,
          "medium_prompt_requests": 0,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 845048.0,
        "unexplained_share": 0.10662950534543095
      },
      {
        "calls": 1,
        "instructions_per_call": 9261479.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 7,
          "medium_prompt_requests": 0,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 998359.0,
        "unexplained_share": 0.1077969296264668
      },
      {
        "calls": 1,
        "instructions_per_call": 10505639.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 8,
          "medium_prompt_requests": 0,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 1107978.0,
        "unexplained_share": 0.10546507451855142
      },
      {
        "calls": 1,
        "instructions_per_call": 3673854.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 3,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 492348.0,
        "unexplained_share": 0.13401403539716059
      },
      {
        "calls": 1,
        "instructions_per_call": 4550739.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 4,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 482102.0,
        "unexplained_share": 0.1059392771152114
      },
      {
        "calls": 1,
        "instructions_per_call": 2314240.0,
        "state": {
          "default_tokenization": 0,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 0,
          "short_prompt_requests": 2
        },
        "unexplained_instructions_per_call": 329949.0,
        "unexplained_share": 0.14257337181969026
      },
      {
        "calls": 1,
        "instructions_per_call": 59669709.0,
        "state": {
          "default_tokenization": 1,
          "long_prompt_requests": 0,
          "medium_prompt_requests": 0,
          "short_prompt_requests": 0
        },
        "unexplained_instructions_per_call": 4106054.0,
        "unexplained_share": 0.068813038789916
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 4,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 14.257337181969026,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 14.257337181969026,
      "iteration": 4,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}