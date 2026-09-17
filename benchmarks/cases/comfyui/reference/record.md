## ComfyUI: the cache costs more than the caching saves

ComfyUI is the most used graph orchestrator for image and video generation, and its
central promise is that re-running a workflow only re-executes what changed. Deciding
what changed means computing a cache key per node, and that is where the time goes.

`CacheKeySetInputSignature.get_node_signature` builds a node's key from a flat list of
every one of its ancestors' immediate signatures, then converts the whole list with
`to_hashable`. `add_keys` does this for every node in the workflow, so the total is
proportional to nodes times depth. It runs on every prompt execution, before any node
does any work, and it is pure Python on the CPU with no model involved.

### Depth, not size

Same node count, three shapes:

| nodes | chain | diamond | wide (no depth) |
|---|---|---|---|
| 100 | 67.8 ms | 80.4 ms | 2.3 ms |
| 200 | 435.8 ms | 523.6 ms | 4.4 ms |
| 400 | 2,016.9 ms | 2,463.1 ms | 9.1 ms |
| 800 | 8,312.4 ms | 10,597.9 ms | 18.2 ms |
| per doubling | 4.1x | 4.3x | 2.0x |

At 800 nodes a deep workflow costs **460x** what a wide one of identical size costs. A
200-node chain, an entirely ordinary ComfyUI workflow, spends 436 ms per run deciding
what to skip.

### drperf

An affine fit in the node count alone leaves 74.4% of the cost irregular, which is the
tool saying the model cannot express what it measured. Declaring the squared state
resolves it:

    cost(n, n_sq) = 56,152.8*n + 318.1*n_sq + -563,031.2     irregular 6.1%

and the breakdown per unit of depth puts 80% of it in one place:

| stage | instructions per unit of depth |
|---|---|
| `to_hashable` | 79,077.5 |
| `immediate_sigs` | 12,434.3 |
| `ancestry` | 7,207.6 |

### The fix, and the bug in the first attempt

Signatures are built bottom-up and memoised: a node's key is its own inputs plus the
already-computed signature of each node it links to, shared by reference. The walk is
iterative so a deep workflow cannot exhaust the stack.

The first attempt passed the assembled structure to `to_hashable`, as the original does,
and the verification caught it immediately: `to_hashable` recognises Mappings and
Sequences, and a frozenset is neither, so every parent signature fell through to the
`Unhashable` sentinel and every key became distinct. It showed up as 1,339 of 1,409
invalidation checks failing, including a downstream node's edit appearing to invalidate
its own ancestors. The key has to be assembled already-hashable instead.

### Verification

What matters is not the key's value but which nodes it treats as equal, and which it
invalidates when one changes. Across 62 workflows, including deliberately duplicated and
deliberately shared subgraphs, and perturbing every node of every workflow in turn:

| check | result |
|---|---|
| equality partition identical | 62 / 62 |
| invalidation set identical | 1,409 / 1,409 |
| ComfyUI's own execution unit tests | 67 passed, identical on both trees |

### Results

| shape, 800 nodes | stock | fixed | |
|---|---|---|---|
| chain | 8,312.4 ms | 4.42 ms | **1,881x** |
| diamond | 10,597.9 ms | 4.66 ms | **2,274x** |
| wide | 18.2 ms | 4.32 ms | 4.2x |

Per-node cost becomes flat at about 5.5 us regardless of shape or size, and every shape
now scales at 2.0x per doubling. The wide case, already linear, still gets 4.2x because
the per-node constant drops. drperf confirms the term is gone rather than reduced:

    stock: cost(n, n_sq) = 56,152.8*n + 318.1*n_sq + -563,031.2
    fixed: cost(n, n_sq) = 41,409.9*n +  0.351*n_sq +   39,287

The quadratic coefficient falls by 906x, and the linear term by 26% as well.

Patch: `comfyui_cachekey.patch`, 53 lines added in one file. Workspace: `comfy/`, with
`probe_cachekey.py`, `drperf_cachekey.py`, `fix_comfy.py` and `verify_comfy.py`.

