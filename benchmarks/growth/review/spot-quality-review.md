# Benchmark group spot review

Reviewed on 2026-09-15: 36 cases. Compiler-frontends and native-libraries use contiguous spot selections (`cf-001..012`, `nl-001..012`). General-libraries uses a deterministic stratified selection: two cases each from NetworkX, NumPy, pandas, urllib3, packaging, and jsonschema. This is not a random or “seeded” sample.

| Group | Selection | Region-verified | Material findings |
|---|---|---:|---:|
| compiler-frontends | cf-001..012 | 12/12 | 0 |
| general-libraries | 2 cases × 6 projects | 12/12 | 0 |
| native-libraries | nl-001..012 | 12/12 | 0 |

## Evidence updates during review

The compiler case manifests initially exposed host-compiler behavior commands that could not establish pinned target entry. Final receipts from the pinned instrumented binary resolve that concern for all 12 selected cases: each target entered at sizes 4, 16, and 64. Entry does not prove every deep branch or loop ran. For example, `ProcessAPINotes` may return early, and entry into `diagnoseOdrViolations` does not itself demonstrate an ODR-violation path.

The general-library group regenerated exact selected-block metadata and its final receipt reports all 12 stratified cases region-verified. This supersedes transient marker misses and an invalid X509 fixture observed while its rerun was in progress.

## Checks that passed

The repository collector check with required tests completed successfully. The reviewed patches contain one empty marker and no PCVs, tasks do not supply a cost formula or optimization answer, source snapshots match declared hashes, and the relevant bundled licenses are present.

The general-library cases compare concrete outputs with pristine implementations on bounded varied inputs and require marker entry. The native-library cases compile the pinned RapidJSON header, exercise their named APIs at sizes 1, 2, 7, 16, and 65, assert concrete state or results, and require balanced marker entry.

The JSON report binds every reviewed manifest, patch, task, reference, source snapshot, test fixture, validation report, compiler entry receipt, and license by SHA-256.

## Limits

This is a bounded spot review. Marker entry proves reachability of the selected region but does not by itself establish coverage of every internal branch.

