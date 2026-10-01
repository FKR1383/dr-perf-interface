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
    "hypothesis": "Remaining unexplained work may arise from sampling-parameter branches. Counting stochastic requests alongside initialization, batch size, and text volume should capture this independent source of variation.",
    "iteration": 7,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Separates the initial call and its substantial initialization work."
      },
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Tracks common rendering and engine-insertion work per request."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else sum((len(p['prompt'] if 'prompt' in p else p) for p in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable))",
        "name": "total_prompt_characters",
        "rationale": "Measures batch text volume without consuming the rendering generator."
      },
      {
        "expression": "sum((1 for p in params if p.temperature > 0))",
        "name": "sampled_requests",
        "rationale": "Counts requests using stochastic sampling, which require different sampling-parameter validation and preparation from greedy requests."
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
        "default_tokenization": 52322821.71006545,
        "request_count": 629218.8474183882,
        "sampled_requests": -11127.843805311722,
        "total_prompt_characters": 1598.0747383324322
      },
      "constant": 495666.43966237135,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 127.8163833739236,
    "max_unexplained_share": 0.28904765493214923,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "request_count",
      "total_prompt_characters",
      "sampled_requests"
    ],
    "raw_files": [
      "run.1786433.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 2297628.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 2,
          "sampled_requests": 1,
          "total_prompt_characters": 54
        },
        "unexplained_instructions_per_call": 543454.0,
        "unexplained_share": 0.23652828047011962
      },
      {
        "calls": 1,
        "instructions_per_call": 3677673.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 3,
          "sampled_requests": 1,
          "total_prompt_characters": 249
        },
        "unexplained_instructions_per_call": 938991.0,
        "unexplained_share": 0.255322047392468
      },
      {
        "calls": 1,
        "instructions_per_call": 4543134.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 4,
          "sampled_requests": 1,
          "total_prompt_characters": 332
        },
        "unexplained_instructions_per_call": 1027198.0,
        "unexplained_share": 0.22609898805538203
      },
      {
        "calls": 1,
        "instructions_per_call": 6900440.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 5,
          "sampled_requests": 2,
          "total_prompt_characters": 780
        },
        "unexplained_instructions_per_call": 1994556.0,
        "unexplained_share": 0.28904765493214923
      },
      {
        "calls": 1,
        "instructions_per_call": 7937505.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 6,
          "sampled_requests": 2,
          "total_prompt_characters": 936
        },
        "unexplained_instructions_per_call": 2186270.0,
        "unexplained_share": 0.2754354170485562
      },
      {
        "calls": 1,
        "instructions_per_call": 9239749.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 7,
          "sampled_requests": 2,
          "total_prompt_characters": 1092
        },
        "unexplained_instructions_per_call": 2548201.0,
        "unexplained_share": 0.27578682061601456
      },
      {
        "calls": 1,
        "instructions_per_call": 10522500.0,
        "state": {
          "default_tokenization": 0,
          "request_count": 8,
          "sampled_requests": 3,
          "total_prompt_characters": 1272
        },
        "unexplained_instructions_per_call": 2905557.0,
        "unexplained_share": 0.276128011404134
      },
      {
        "calls": 1,
        "instructions_per_call": 59669293.0,
        "state": {
          "default_tokenization": 1,
          "request_count": 1,
          "sampled_requests": 0,
          "total_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 6302275.0,
        "unexplained_share": 0.10562007161707111
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 7,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 28.904765493214924,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 28.904765493214924,
      "iteration": 7,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}