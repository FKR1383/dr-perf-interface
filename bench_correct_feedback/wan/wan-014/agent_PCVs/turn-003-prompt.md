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

This is iteration 3. Use your retained benchmark and candidate history. The trusted script returned the complete Dr. Perf metrics report for the previous submitted candidate, followed by its deterministic decision.

{
  "candidate": {
    "hypothesis": "The persistent unexplained work across all six shape/cache states suggests runtime variability. Replacing the boundary correction with garbage-collector entry state tests whether allocation history explains that variation.",
    "iteration": 2,
    "pcvs": [
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4]",
        "name": "latent_volume",
        "rationale": "Captures the dominant spatial scaling of decoder operations."
      },
      {
        "expression": "x.shape[0] * x.shape[2] * x.shape[3] * x.shape[4] if feat_cache is not None and feat_cache[feat_idx[0]] is not None else 0",
        "name": "cached_latent_volume",
        "rationale": "Captures the additional volume-dependent work from temporal upsampling on cached chunks."
      },
      {
        "expression": "int(feat_cache is not None and feat_cache[feat_idx[0]] is not None)",
        "name": "has_cached_features",
        "rationale": "Separates fixed overhead for initial and cached chunks."
      },
      {
        "expression": "__import__('gc').get_count()[0]",
        "name": "gc_allocation_balance",
        "rationale": "Cheap runtime entry state that may explain allocation and garbage-collection variability within otherwise identical decoder shapes."
      }
    ]
  },
  "case_id": "wan-014",
  "drperf_full_report": {
    "automatic_regime_splitting": false,
    "calls": 36,
    "case": "wan-014",
    "distinct_states": 36,
    "dropped_calls": 0,
    "formula": {
      "coefficients": {
        "cached_latent_volume": 1818926.9428844121,
        "gc_allocation_balance": 1.9204389213423112,
        "has_cached_features": 5409018.000087577,
        "latent_volume": 667173.1445595637
      },
      "constant": 12687626.404390715,
      "dependent_columns": []
    },
    "gate_pass": false,
    "gate_reasons": [
      "unexplained share exceeds 5% at an observed state"
    ],
    "instruction_scope": "target own work, excluding configured runtime waiting modules; marker overhead included",
    "instrumented_wall_seconds": 47.390663540922105,
    "max_unexplained_share": 0.4238945295012842,
    "nested_calls_per_call": 0.0,
    "pcv_names": [
      "latent_volume",
      "cached_latent_volume",
      "has_cached_features",
      "gc_allocation_balance"
    ],
    "raw_files": [
      "run.1546035.json"
    ],
    "required_states": 6,
    "returncode": 0,
    "states": [
      {
        "calls": 1,
        "instructions_per_call": 21257438.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 17,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 5991444.0,
        "unexplained_share": 0.28185165117263894
      },
      {
        "calls": 1,
        "instructions_per_call": 21238574.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 30,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 5972017.0,
        "unexplained_share": 0.28118728686775296
      },
      {
        "calls": 1,
        "instructions_per_call": 21284134.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 38,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 6017323.0,
        "unexplained_share": 0.2827140159895629
      },
      {
        "calls": 1,
        "instructions_per_call": 21260999.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 40,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 5994219.0,
        "unexplained_share": 0.28193496457998046
      },
      {
        "calls": 1,
        "instructions_per_call": 21246000.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 51,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 5978801.0,
        "unexplained_share": 0.2814083121528758
      },
      {
        "calls": 1,
        "instructions_per_call": 21238887.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 53,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 5971995.0,
        "unexplained_share": 0.28118210714149006
      },
      {
        "calls": 1,
        "instructions_per_call": 21549226.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 169,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 6268129.0,
        "unexplained_share": 0.29087490195703547
      },
      {
        "calls": 1,
        "instructions_per_call": 21286925.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 226,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 6020268.0,
        "unexplained_share": 0.28281529624405594
      },
      {
        "calls": 1,
        "instructions_per_call": 21273773.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 236,
          "has_cached_features": 0,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 6006518.0,
        "unexplained_share": 0.2823438042701687
      },
      {
        "calls": 1,
        "instructions_per_call": 41195569.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 61,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13122586.0,
        "unexplained_share": 0.31854362783531404
      },
      {
        "calls": 1,
        "instructions_per_call": 41163875.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 63,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13091166.0,
        "unexplained_share": 0.3180255989019498
      },
      {
        "calls": 1,
        "instructions_per_call": 41633490.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 66,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13393444.0,
        "unexplained_share": 0.321698805456857
      },
      {
        "calls": 1,
        "instructions_per_call": 41177666.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 74,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13104692.0,
        "unexplained_share": 0.3182475665327899
      },
      {
        "calls": 1,
        "instructions_per_call": 41170898.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 76,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13098113.0,
        "unexplained_share": 0.3181400852611959
      },
      {
        "calls": 1,
        "instructions_per_call": 41689424.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 79,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13450199.0,
        "unexplained_share": 0.32262856402141704
      },
      {
        "calls": 1,
        "instructions_per_call": 44724891.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 256,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 16525243.0,
        "unexplained_share": 0.36948649019625335
      },
      {
        "calls": 1,
        "instructions_per_call": 41221799.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 259,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13148945.0,
        "unexplained_share": 0.31898037734840246
      },
      {
        "calls": 1,
        "instructions_per_call": 41708006.0,
        "state": {
          "cached_latent_volume": 4,
          "gc_allocation_balance": 262,
          "has_cached_features": 1,
          "latent_volume": 4
        },
        "unexplained_instructions_per_call": 13468755.0,
        "unexplained_share": 0.3229297272087282
      },
      {
        "calls": 1,
        "instructions_per_call": 34754814.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 39,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 11500666.0,
        "unexplained_share": 0.3309085757155829
      },
      {
        "calls": 1,
        "instructions_per_call": 34751529.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 41,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 11495700.0,
        "unexplained_share": 0.330796955725315
      },
      {
        "calls": 1,
        "instructions_per_call": 34732368.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 52,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 11477976.0,
        "unexplained_share": 0.3304691462442181
      },
      {
        "calls": 1,
        "instructions_per_call": 34728852.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 54,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 11473306.0,
        "unexplained_share": 0.3303681331015491
      },
      {
        "calls": 1,
        "instructions_per_call": 34760266.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 235,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 11505508.0,
        "unexplained_share": 0.3309959710895193
      },
      {
        "calls": 1,
        "instructions_per_call": 34755119.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 237,
          "has_cached_features": 0,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 11499172.0,
        "unexplained_share": 0.33086268529248886
      },
      {
        "calls": 1,
        "instructions_per_call": 87390656.0,
        "state": {
          "cached_latent_volume": 16,
          "gc_allocation_balance": 64,
          "has_cached_features": 1,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 29593806.0,
        "unexplained_share": 0.33863810336885447
      },
      {
        "calls": 1,
        "instructions_per_call": 87384817.0,
        "state": {
          "cached_latent_volume": 16,
          "gc_allocation_balance": 77,
          "has_cached_features": 1,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 29588417.0,
        "unexplained_share": 0.33859906120762373
      },
      {
        "calls": 1,
        "instructions_per_call": 93689863.0,
        "state": {
          "cached_latent_volume": 16,
          "gc_allocation_balance": 260,
          "has_cached_features": 1,
          "latent_volume": 16
        },
        "unexplained_instructions_per_call": 35799674.0,
        "unexplained_share": 0.38210829703102456
      },
      {
        "calls": 1,
        "instructions_per_call": 57567269.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 42,
          "has_cached_features": 0,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 20907432.0,
        "unexplained_share": 0.3631826272668936
      },
      {
        "calls": 1,
        "instructions_per_call": 57565777.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 55,
          "has_cached_features": 0,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 20905864.0,
        "unexplained_share": 0.3631648018926245
      },
      {
        "calls": 1,
        "instructions_per_call": 63696295.0,
        "state": {
          "cached_latent_volume": 0,
          "gc_allocation_balance": 238,
          "has_cached_features": 0,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 27000511.0,
        "unexplained_share": 0.4238945295012842
      },
      {
        "calls": 1,
        "instructions_per_call": 168345486.0,
        "state": {
          "cached_latent_volume": 36,
          "gc_allocation_balance": 65,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 60716360.0,
        "unexplained_share": 0.36066520963918214
      },
      {
        "calls": 1,
        "instructions_per_call": 169163503.0,
        "state": {
          "cached_latent_volume": 36,
          "gc_allocation_balance": 68,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 61374752.0,
        "unexplained_share": 0.36281320090658087
      },
      {
        "calls": 1,
        "instructions_per_call": 168341940.0,
        "state": {
          "cached_latent_volume": 36,
          "gc_allocation_balance": 78,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 60712651.0,
        "unexplained_share": 0.3606507742515026
      },
      {
        "calls": 1,
        "instructions_per_call": 169160496.0,
        "state": {
          "cached_latent_volume": 36,
          "gc_allocation_balance": 81,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 61371651.0,
        "unexplained_share": 0.36280131857735864
      },
      {
        "calls": 1,
        "instructions_per_call": 177135742.0,
        "state": {
          "cached_latent_volume": 36,
          "gc_allocation_balance": 261,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 69411982.0,
        "unexplained_share": 0.39185757327281806
      },
      {
        "calls": 1,
        "instructions_per_call": 169167113.0,
        "state": {
          "cached_latent_volume": 36,
          "gc_allocation_balance": 264,
          "has_cached_features": 1,
          "latent_volume": 36
        },
        "unexplained_instructions_per_call": 61377544.0,
        "unexplained_share": 0.3628219629189983
      }
    ],
    "sufficient_points": true,
    "threshold": 0.05,
    "validity_warnings": []
  },
  "fixed_workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401",
  "iteration": 2,
  "script_decision": {
    "assessment": {
      "irregularity_percent": 42.38945295012842,
      "reasons": [],
      "success": false,
      "threshold_percent": 10.0,
      "valid": true
    },
    "feedback": {
      "comparison": "strictly-less-than",
      "irregularity_percent": 42.38945295012842,
      "iteration": 2,
      "status": "retry",
      "threshold_percent": 10.0
    },
    "workload_digest": "809da3f64a987bd3ba6f9e443583137895446b96414c5e0c2546f4abbd544401"
  }
}