"""Does the rebuilt cache key treat the same nodes as equal, and invalidate the same ones?

Two properties matter, and neither is about the key's value:

  1. Partition. Two nodes share a key under the new scheme exactly when they shared one
     under the old, so nothing that was cached separately now collides.
  2. Invalidation. Changing one node's parameter changes exactly the same set of keys,
     so nothing stale survives and nothing fresh is needlessly thrown away.

Random graphs are generated with shared subgraphs, duplicated subgraphs, diamonds and
chains, since those are where the two schemes could plausibly disagree.
"""
import asyncio, copy, importlib, random, sys, types


def load(tree, tag):
    for m in [k for k in sys.modules if k.startswith(("comfy_execution", "comfy.", "nodes"))]:
        del sys.modules[m]
    sys.path.insert(0, tree)

    class _FakeNode:
        NOT_IDEMPOTENT = False

        @staticmethod
        def INPUT_TYPES():
            return {"required": {}}

    ns = types.ModuleType("nodes")
    ns.NODE_CLASS_MAPPINGS = {c: _FakeNode for c in ("Src", "Chain", "Merge", "Sink")}
    sys.modules["nodes"] = ns
    mp = types.ModuleType("comfy.model_patcher")
    mp.is_model_patcher_output = lambda x: False
    sys.modules["comfy.model_patcher"] = mp
    sm = types.ModuleType("comfy.system_memory")
    sm.virtual_memory_available = lambda: 1 << 40
    sys.modules["comfy.system_memory"] = sm

    caching = importlib.import_module("comfy_execution.caching")
    graph = importlib.import_module("comfy_execution.graph")
    sys.path.remove(tree)
    return caching, graph


class StubIsChanged:
    async def get(self, node_id):
        return False


async def keys_for(caching, graph, prompt):
    node_ids = list(prompt.keys())
    ks = caching.CacheKeySetInputSignature(graph.DynamicPrompt(prompt), node_ids,
                                           StubIsChanged())
    await ks.add_keys(node_ids)
    return {nid: ks.get_data_key(nid) for nid in node_ids}


def partition(keys):
    groups = {}
    for nid, k in keys.items():
        groups.setdefault(k, set()).add(nid)
    return frozenset(frozenset(g) for g in groups.values())


def random_prompt(rng, n):
    prompt = {"0": {"class_type": "Src", "inputs": {"seed": rng.randint(0, 3)}}}
    for i in range(1, n):
        kind = rng.random()
        parents = [str(rng.randrange(i))]
        if kind < 0.3 and i > 2:
            parents.append(str(rng.randrange(i)))
        inputs = {f"in{j}": [p, 0] for j, p in enumerate(parents)}
        inputs["param"] = rng.choice([0, 1, "a", "b"])
        prompt[str(i)] = {"class_type": rng.choice(["Chain", "Merge", "Sink"]),
                          "inputs": inputs}
    return prompt


def duplicated_subgraph_prompt():
    """Two structurally identical but separate branches feeding one node."""
    p = {}
    for tag in ("a", "b"):
        p[f"src_{tag}"] = {"class_type": "Src", "inputs": {"seed": 7}}
        p[f"mid_{tag}"] = {"class_type": "Chain",
                           "inputs": {"x": [f"src_{tag}", 0], "param": 1}}
    p["join"] = {"class_type": "Merge",
                 "inputs": {"x": ["mid_a", 0], "y": ["mid_b", 0]}}
    return p


def shared_subgraph_prompt():
    """One branch feeding one node twice: the sharing case."""
    p = {"src": {"class_type": "Src", "inputs": {"seed": 7}}}
    p["mid"] = {"class_type": "Chain", "inputs": {"x": ["src", 0], "param": 1}}
    p["join"] = {"class_type": "Merge", "inputs": {"x": ["mid", 0], "y": ["mid", 0]}}
    return p


async def main():
    old = load("/home/ubuntu/drperf-cases/comfy/ComfyUI", "old")
    new = load("/home/ubuntu/drperf-cases/comfy/ComfyUI-fix", "new")

    rng = random.Random(0)
    cases = [("duplicated subgraph", duplicated_subgraph_prompt()),
             ("shared subgraph", shared_subgraph_prompt())]
    for i in range(60):
        cases.append((f"random {i}", random_prompt(rng, rng.randint(4, 40))))

    part_same = part_diff = 0
    inval_same = inval_diff = 0
    diffs = []

    for name, prompt in cases:
        ko = await keys_for(*old, prompt)
        kn = await keys_for(*new, prompt)
        po, pn = partition(ko), partition(kn)
        if po == pn:
            part_same += 1
        else:
            part_diff += 1
            coarser = all(any(g <= h for h in pn) for g in po)
            diffs.append((name, "new is coarser (merges duplicates)" if coarser
                          else "PARTITIONS DIVERGE"))

        # invalidation: perturb every node in turn, compare which keys move
        for target in list(prompt.keys()):
            p2 = copy.deepcopy(prompt)
            p2[target]["inputs"]["param"] = "PERTURBED"
            ko2 = await keys_for(*old, p2)
            kn2 = await keys_for(*new, p2)
            moved_o = {n for n in prompt if ko.get(n) != ko2.get(n)}
            moved_n = {n for n in prompt if kn.get(n) != kn2.get(n)}
            if moved_o == moved_n:
                inval_same += 1
            else:
                inval_diff += 1
                if len(diffs) < 6:
                    diffs.append((f"{name}/perturb {target}",
                                  f"old moved {sorted(moved_o)}, new moved {sorted(moved_n)}"))

    print(f"cases: {len(cases)}")
    print(f"partition identical:      {part_same}/{len(cases)}")
    print(f"partition differing:      {part_diff}")
    print(f"invalidation identical:   {inval_same}/{inval_same+inval_diff}")
    print(f"invalidation differing:   {inval_diff}")
    if diffs:
        print("\ndifferences:")
        for n, d in diffs[:10]:
            print(f"  {n}: {d}")
    else:
        print("\nno differences found")


if __name__ == "__main__":
    asyncio.run(main())
