# Rodinia Backpropagation: CPU neural-network training

This case uses the C backpropagation implementation from the
[Rodinia benchmark suite](https://www.cs.virginia.edu/~skadron/lava/rodinia/).
It trains a fully connected network with one hidden layer. Inputs, targets and
initial weights are generated in memory; no image files, documents, database,
model download or external dataset is needed.

The experiment varies network dimensions and the number of training steps.
The source is pinned to Rodinia 3.1 commit
`31d0ebf5adaf3aaa6c770cc5319a62275d8c1881` in the
[source mirror](https://github.com/yuhc/gpu-rodinia/tree/31d0ebf5adaf3aaa6c770cc5319a62275d8c1881/openmp/backprop).
Source hashes, the upstream license and the unmodified source files are retained
in the prepared workspace.

## Prepare

Build Dr. Perf first with `./build.sh`, then run from the repository root:

```sh
python3 evaluation/case_studies/rodinia_backprop/prepare.py
```

This prepares `build/evaluation-rodinia-backprop`, builds its executable and
checks two training steps against an independent numerical gradient, including
the momentum update. It refuses to overwrite an existing workspace; select a
different destination with `--workspace` when preparing another copy.

The prepared program is a **serial CPU adaptation**: only the upstream `OPEN`
configuration is disabled. The original forward propagation, error computation
and weight-update functions are unchanged. The new driver varies dimensions,
repeats training steps, and generates scaled initial weights. This is an
evaluation case based on Rodinia, not a result from Rodinia's default setup.

## Region

`train_region` in `driver.c` measures the training loop and all its callees:

```c
perfmark_begin("train", "net->input_n", (int64_t)net->input_n);
for (int step = 0; step < steps; ++step)
    bpnn_train(net, output_error, hidden_error);
perfmark_end("train");
```

`bpnn_train`, in `rodinia/backprop.c`, performs forward propagation through both
weight matrices, computes output and hidden errors, and updates both matrices
using gradient descent with momentum. Allocation, initialization, numerical
checks, output checks, printing and deallocation are outside the marked region.
The agent may replace the initial state declaration.

## Run the evaluation

An authenticated Codex CLI must be on PATH. After preparing the workspace, run:

```sh
python3 evaluation/run.py \
  --workspace build/evaluation-rodinia-backprop \
  --region train \
  --max-attempts 10 \
  --target-irregularity 0.10 \
  --results-dir "evaluation/results/rodinia-backprop-$(date +%Y%m%d-%H%M%S)" \
  -- ./program --cases 96 --shape-seed 17 --data-seed 7
```

The command fixes all workload values across agent attempts. The generated
networks vary four controls:

| Control | Allowed values/range |
| --- | --- |
| Input units | 64–4096, in multiples of 16 |
| Hidden units | 8, 16, 24, 32, 48, 64, 96, 128 |
| Output units | 1, 2, 4, 8, 16, 32, 64 |
| Training steps | 1, 2, 3, 4, 6, 8, 12, 16 |

`--shape-seed` chooses the fixed sequence of configurations. `--data-seed`
generates the numeric inputs, targets and weights independently of that choice.
The driver prints each configuration and a checksum after its measured call.
Every case starts from a fresh network. Seed 17 produces 96 different input
widths, so the initial size-only declaration cannot average different network
shapes at the same input width. The driver permits at most 120 cases per run
to stay below the 128-state-combination measurement limit.

This is intended to exercise feature discovery across interacting dimensions
and several compute stages. It does not guarantee that the agent will miss a
feature or meet the irregularity target. The program checks that activations,
errors and weights stay finite; these checks are distinct from the small
numerical-gradient correctness test.

## Reserved follow-up checks

These configurations are kept out of the prepared agent workspace documentation.
Use them after discovery, keeping the selected features and coefficients fixed:

```sh
# Same network shapes; different generated numeric values.
./program --cases 96 --shape-seed 17 --data-seed 29

# Different shapes and numeric values.
./program --cases 96 --shape-seed 101 --data-seed 29
```

Run these from the prepared workspace. They check ordinary program execution;
they do not themselves calculate frozen-model prediction error. In this prepared
case, the 96 validation shape tuples are disjoint from the discovery tuples.
Do not start a fresh agent search on these configurations and describe its
newly fitted formula as validation of the original formula.

Generated data and fixed loop bounds make the main workload more controlled,
but do not prove that instruction counts are completely independent of numeric
values: sigmoid evaluation and error-sign branches can still vary. Compare
individual calls and held-out shapes, as well as Dr. Perf irregularity.
