"""Price ComfyUI's cache-key computation with drperf, broken down by stage.

The bodies of `add_keys`, `get_node_signature`, `get_ordered_ancestry_internal` and
`get_immediate_node_signature` are copied from comfy_execution/caching.py with only
region markers added, so each stage's cost function stands on its own.
"""
import asyncio, os, sys, types

sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")
ROOT = os.environ.get("COMFY_TREE", "/home/ubuntu/drperf-cases/comfy/ComfyUI")
sys.path.insert(0, ROOT)

import perfmark


class _FakeNode:
    NOT_IDEMPOTENT = False

    @staticmethod
    def INPUT_TYPES():
        return {"required": {}}


nodes_stub = types.ModuleType("nodes")
nodes_stub.NODE_CLASS_MAPPINGS = {"Chain": _FakeNode, "Src": _FakeNode}
sys.modules["nodes"] = nodes_stub
mp = types.ModuleType("comfy.model_patcher")
mp.is_model_patcher_output = lambda x: False
sys.modules["comfy.model_patcher"] = mp
sm = types.ModuleType("comfy.system_memory")
sm.virtual_memory_available = lambda: 1 << 40
sys.modules["comfy.system_memory"] = sm

from comfy_execution.caching import CacheKeySetInputSignature, to_hashable
from comfy_execution.graph import DynamicPrompt


class StubIsChanged:
    async def get(self, node_id):
        return False


IS_FIXED = hasattr(CacheKeySetInputSignature, "get_linked_node_signature")


if IS_FIXED:
    # The fixed tree computes signatures bottom-up; there are no per-ancestor stages to
    # mark, so only the whole-workflow region is measured and the comparison stays fair.
    Marked = CacheKeySetInputSignature
else:
    class Marked(CacheKeySetInputSignature):
        """The stock code, with its three stages marked."""

        async def get_node_signature(self, dynprompt, node_id):
            signature = []
            depth = int(node_id)      # in a chain this is exactly the ancestor count
            with perfmark.region("ancestry", depth=depth):
                ancestors, order_mapping = self.get_ordered_ancestry(dynprompt, node_id)
            with perfmark.region("immediate_sigs", depth=depth):
                signature.append(await self.get_immediate_node_signature(
                    dynprompt, node_id, order_mapping))
                for ancestor_id in ancestors:
                    signature.append(await self.get_immediate_node_signature(
                        dynprompt, ancestor_id, order_mapping))
            with perfmark.region("to_hashable", depth=depth):
                return to_hashable(signature)


def chain_prompt(n):
    prompt = {"0": {"class_type": "Src", "inputs": {"seed": 0}}}
    for i in range(1, n):
        prompt[str(i)] = {"class_type": "Chain",
                          "inputs": {"x": [str(i - 1), 0], "strength": i * 0.1}}
    return prompt


async def main():
    st = perfmark.states(n=200)
    n = int(st["n"])
    prompt = chain_prompt(n)
    node_ids = list(prompt.keys())
    dyn = DynamicPrompt(prompt)
    ks = Marked(dyn, node_ids, StubIsChanged())
    # n_sq declared alongside n: the cost is expected to be quadratic in the
    # node count, and an affine fit in n alone cannot express that.
    with perfmark.region("add_keys", n=n, n_sq=n * n):
        await ks.add_keys(node_ids)
    print(f"n={n} keys={len(ks.keys)}")


if __name__ == "__main__":
    asyncio.run(main())
