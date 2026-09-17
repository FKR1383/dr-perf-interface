# Rodinia k-means: CPU clustering through convergence

This case uses the serial C k-means implementation from the
[Rodinia benchmark suite](https://rodinia.cs.virginia.edu/), pinned to commit
`31d0ebf5adaf3aaa6c770cc5319a62275d8c1881`. The upstream clustering source is
unchanged. Preparation verifies its SHA-256 and retains the original source,
license, and provenance in the workspace.

The new driver generates numerical points in memory. It needs no input files,
database, downloaded model, or external dataset. This controls how inputs are
created; it does **not** make execution independent of their values.

Unlike the Backprop case, this case runs until convergence, rather than for a
fixed number of steps. Point sets with identical dimensions can require very
different amounts of work. This is a test of the limits of entry-state cost
modelling, not a promised example of Dr. Perf outperforming static reasoning.

## Prepare and run

From the repository root, with Dr. Perf already built:

```sh
python3 evaluation/case_studies/rodinia_kmeans/prepare.py
```

Preparation builds the program and checks known one- and two-cluster answers,
duplicate points, and an empty cluster. It refuses to overwrite an existing
workspace; use `--workspace` to choose another destination.

With an authenticated Codex CLI on PATH:

```sh
python3 evaluation/run.py \
  --workspace build/evaluation-rodinia-kmeans \
  --region cluster \
  --max-attempts 10 \
  --target-irregularity 0.10 \
  --results-dir "evaluation/results/rodinia-kmeans-$(date +%Y%m%d-%H%M%S)" \
  -- ./program --shapes 24 --shape-seed 17 --data-seed 7
```

There are 24 shapes and three coordinate distributions per shape: **72 calls**
per measurement. `--shapes` accepts 1–40, keeping the total below the client's
128-state-combination limit. Point counts are distinct across shapes, drawn
from 256–2048 in multiples of 32. Dimensions and cluster counts independently
come from `{2, 4, 8, 16}`. Separate seeds select shapes and numeric coordinates.

The three distributions are separated blobs, a uniform cloud, and an elongated
correlated cloud. Every call starts with fresh points. The original kernel
chooses the first `nclusters` points as initial centers. The stopping threshold
is zero, so assignments must stop changing. In this upstream implementation,
`delta` is a count of changed assignments, not a fraction.

## Region

`cluster_region` in `driver.c` wraps the full clustering call:

```c
const char *names[] = {"npoints", "nfeatures", "nclusters"};
const int64_t values[] = {npoints, nfeatures, nclusters};
perfmark_begin_v("cluster", 3, names, values);
float **clusters = kmeans_clustering(feature, nfeatures, npoints,
                                    nclusters, threshold, membership);
perfmark_end("cluster");
```

The measured call initializes centers, repeatedly assigns points to their
nearest center and updates means, and stops when assignments stabilize. Its
internal allocation and cleanup are included. Point generation, output checks,
printing, and cleanup of returned arrays are outside the region. The agent may
replace the initial state declarations while preserving this boundary.

After every call the driver independently checks finite centers, valid
nearest-center assignments, and agreement between nonempty centers and their
members' means. These check a converged fixed point, not a global optimum.

## Interpretation and validation

- The eventual iteration count is produced during the region. Recording it
  afterward can explain observed work, but does not make it a legal entry
  feature. Re-running clustering before the marker to obtain it is also invalid.
- Seeds, shape numbers, and generator-family labels are experimental metadata;
  do not use them as substitute cost predictors. Any proposed feature must
  describe the actual program state at entry under the evaluation contract.
- The initial three states deliberately group three different coordinate sets
  under each shape. Dr. Perf averages calls with equal declared states. A low
  score for such averages can hide large per-call errors; inspect individual
  trace costs as well as the reported irregularity.
- Compare mathematical dependencies, not just spelling or feature count.
  Combining terms that Agent Only already identified is not a newly discovered
  dependency. The harness measures Agent Only's frozen feature set after both
  discovery sessions finish. An unavailable baseline score is not a measured
  failure to predict cost. Validate both models before claiming a quantitative win.
- If both methods fail under the same entry-feature rules, record that outcome.
  It can expose a limitation of the model class or feedback process. It is not
  automatically an agent-discovery success because the workload is difficult.

After selecting a model, keep **both its features and full-precision
coefficients fixed** and test new inputs. From the prepared workspace:

```sh
# Same shapes, different generated coordinates.
./program --shapes 24 --shape-seed 17 --data-seed 29

# A different shape sample and different generated coordinates.
./program --shapes 24 --shape-seed 101 --data-seed 29
```

These commands execute and validate clustering outputs; they do not calculate
frozen-model prediction errors. Measuring those errors requires instrumenting
the selected entry features and comparing the original formula with individual
instruction counts. Refitting a new formula is a separate experiment.

Keep this protocol and any preflight diagnostics outside the agent workspace.
The prepared workspace contains implementation and usage documentation, without
observed iteration counts, measured cost tables, or suggested predictors.
