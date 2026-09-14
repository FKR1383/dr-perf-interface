# Evaluator judgment format

Store actual session submissions and evaluator labels in the following shape.
The example is illustrative, not a measurement result. Each pair must use the
same case, seed, model and measurement budget. Include both `timing` and
`drperf` sessions. Round 0 is the code-only submission; subsequent rounds are
the complete current answer after each measurement, not just newly added claims.
For the small-input experiment set `"track": "small-to-large"` on both sessions;
omitting it selects `discovery`. Score each track separately. These judgments
score semantic claims; they do not compute held-out count-prediction errors or
profiling time saved.

```json
{
  "sessions": [
    {
      "case": "sqlglot",
      "family": "sqlglot-optimizer",
      "seed": 0,
      "model": "record-exact-model-id",
      "condition": "timing",
      "budget": 3,
      "rounds": [
        {"round": 0, "claims": [], "judgments": {}},
        {
          "round": 1,
          "claims": [
            {
              "id": "claim-1",
              "region": "sqlglot.optimizer.optimize",
              "expression": "n and n*n, where n is the number of joined tables",
              "evidence": "Reference the actual source lines and round/input observations here."
            }
          ],
          "judgments": {
            "claim-1": {
              "accepted": true,
              "supports": ["f1"],
              "reason": "Evaluator explanation of the supported dependency, location and evidence."
            }
          }
        }
      ]
    }
  ]
}
```

`supports` references factors in that case's `reference/answer.json`. Acceptance
requires correct localization, expression, entry-state availability, reasonable
annotation cost, and supporting evidence. Reject unsupported extra dependencies
even if a claim also contains a correct one; ask reviewers to grade atomic claims.
Supported novel findings require updating the reviewed answer key consistently
for both conditions, not silently scoring them as false positives.

An early-stopping session carries its final answer through the remaining budget.
An unanswered task is an empty submission, not an omitted pair. Record agent
failures in the experiment manifest; do not drop them from the denominator.
Infrastructure failures should be reported separately and any rerun policy
chosen before comparing conditions. This scorer validates pair completeness,
but does not authenticate transcripts or perform the semantic judgments.
