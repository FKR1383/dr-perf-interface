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
    "hypothesis": "Exact batch character counts and a simple word-count estimate should explain tokenizer work more accurately than prompt-length categories, especially for heterogeneous short prompts and the final batch's modified prefixes.",
    "iteration": 6,
    "pcvs": [
      {
        "expression": "1 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else 0",
        "name": "default_tokenization",
        "rationale": "Separates the initial call and its substantial initialization cost."
      },
      {
        "expression": "len(params)",
        "name": "request_count",
        "rationale": "Tracks common rendering and engine-insertion work per request."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else sum((len(p['prompt'] if 'prompt' in p else p) for p in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable))",
        "name": "total_prompt_characters",
        "rationale": "Measures actual batch text size, including variations that the first-prompt approximation missed, without consuming the rendering generator."
      },
      {
        "expression": "0 if prompts.gi_frame.f_locals.get('tokenization_kwargs') is None else sum(((p['prompt'] if 'prompt' in p else p).count(' ') + 1 for p in prompts.gi_frame.f_locals['.0'].gi_frame.f_locals['self'].iterable))",
        "name": "prompt_word_work",
        "rationale": "Provides a cheap lexical-unit estimate for tokenization work, distinguishing texts with different word lengths."
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
        "default_tokenization": 54463120.81091616,
        "prompt_word_work": -4868.7874284251575,
        "request_count": 630358.2216390063,
        "total_prompt_characters": 3731.2761919628156
      },
      "constant": 646462.625463406,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 140.70937906112522,
    "max_unexplained_share": 0.13702826546967395,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "default_tokenization",
      "request_count",
      "total_prompt_characters",
      "prompt_word_work"
    ],
    "raw_files": [
      "run.1785364.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 2299095.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 12,
          "request_count": 2,
          "total_prompt_characters": 54
        },
        "unexplained_instructions_per_call": 315041.0,
        "unexplained_share": 0.13702826546967395
      },
      {
        "calls": 1,
        "instructions_per_call": 3676122.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 48,
          "request_count": 3,
          "total_prompt_characters": 249
        },
        "unexplained_instructions_per_call": 484189.0,
        "unexplained_share": 0.13171189639516862
      },
      {
        "calls": 1,
        "instructions_per_call": 4547926.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 64,
          "request_count": 4,
          "total_prompt_characters": 332
        },
        "unexplained_instructions_per_call": 465021.0,
        "unexplained_share": 0.10224902516003999
      },
      {
        "calls": 1,
        "instructions_per_call": 6904508.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 140,
          "request_count": 5,
          "total_prompt_characters": 780
        },
        "unexplained_instructions_per_call": 837067.0,
        "unexplained_share": 0.1212348512015628
      },
      {
        "calls": 1,
        "instructions_per_call": 7915392.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 168,
          "request_count": 6,
          "total_prompt_characters": 936
        },
        "unexplained_instructions_per_call": 823300.0,
        "unexplained_share": 0.10401253658694351
      },
      {
        "calls": 1,
        "instructions_per_call": 9260634.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 196,
          "request_count": 7,
          "total_prompt_characters": 1092
        },
        "unexplained_instructions_per_call": 988151.0,
        "unexplained_share": 0.1067044653746169
      },
      {
        "calls": 1,
        "instructions_per_call": 10516881.0,
        "state": {
          "default_tokenization": 0,
          "prompt_word_work": 228,
          "request_count": 8,
          "total_prompt_characters": 1272
        },
        "unexplained_instructions_per_call": 1098782.0,
        "unexplained_share": 0.10447793409471877
      },
      {
        "calls": 1,
        "instructions_per_call": 59691634.0,
        "state": {
          "default_tokenization": 1,
          "prompt_word_work": 0,
          "request_count": 1,
          "total_prompt_characters": 0
        },
        "unexplained_instructions_per_call": 4047638.0,
        "unexplained_share": 0.06780913385617823
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118",
  "iteration": 6,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 13.702826546967394,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 13.702826546967394,
      "iteration": 6,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "b05fa43138c9699604b0b5b6cf1ba6f0f83c4757d5b0053d014f8f12bf458118"
  }
}