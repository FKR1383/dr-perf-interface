"""Bounded native vLLM correctness and marker-reachability scenarios."""
import argparse
import os
import sys
from pathlib import Path


def _args():
    p = argparse.ArgumentParser()
    p.add_argument("--source-root", required=True)
    return p.parse_args()


def _request(i, priority=0, arrival=None):
    from vllm import SamplingParams
    from vllm.v1.request import Request
    return Request(str(i), [1, 2 + i, 3], SamplingParams(max_tokens=1), None,
                   priority=priority, arrival_time=float(i if arrival is None else arrival))


def _queue_scenario(case_id):
    from vllm.v1.core.sched.request_queue import FCFSRequestQueue, PriorityRequestQueue
    n = int(case_id[-3:])
    cls = FCFSRequestQueue if n < 20 else PriorityRequestQueue
    q = cls()
    a, b, c = _request(1, 2, 1), _request(2, 0, 2), _request(3, 1, 3)
    if n in (14, 20):
        for r in (a, b, c): q.add_request(r)
        assert len(q) == 3
    elif n in (15, 21):
        for first, second in ((a,b), (b,c), (c,a)):
            q = cls(); q.add_request(first); q.add_request(second)
            expected = first if n == 15 else min((first,second))
            assert q.peek_request() is expected and len(q) == 2
    elif n in (16, 22):
        for r in (a, b, c): q.add_request(r)
        expected = [a, b, c] if n == 16 else [b, c, a]
        assert [q.pop_request() for _ in range(3)] == expected
    elif n in (17, 23):
        for first, second in ((a,b), (b,c), (c,a)):
            q = cls(); q.add_request(first); q.prepend_request(second)
            expected = second if n == 17 else min((first,second))
            assert q.peek_request() is expected
    elif n in (18, 24):
        for incoming in ((b,), (b,c), (c,a,b)):
            q = cls(); q.add_request(a); other = cls()
            for r in incoming: other.add_request(r)
            q.prepend_requests(other)
            assert len(q) == 1 + len(incoming) and set(q) == ({a} | set(incoming))
    else:
        for removed in (a,b,c):
            q = cls()
            for r in (a,b,c): q.add_request(r)
            q.remove_request(removed)
            assert len(q) == 2 and removed not in q


def _request_scenario():
    from vllm import SamplingParams
    for i, limit in enumerate((1, 2, 4)):
        r = _request(i)
        r2 = __import__('vllm.v1.request', fromlist=['Request']).Request(
            f"x{i}", [1, 2, 3, i], SamplingParams(max_tokens=limit), None,
            priority=i, arrival_time=float(i))
        assert r2.request_id == f"x{i}" and r2.max_tokens == limit
        assert r2.num_prompt_tokens == 4


def _penalty_scenario(case_id):
    import torch
    from vllm.v1.sample.ops.penalties import _convert_to_tensors, apply_all_penalties
    if case_id == 'vllm-050':
        for rows, shape in [([[1,2],[3],[]],(3,2)), ([[4]],(1,1)), ([[],[]],(2,0))]:
            out = _convert_to_tensors(rows, 8, torch.device('cpu'))
            assert tuple(out.shape) == shape
    else:
        for scale in (0.0, 0.1, 0.2):
            rows = [[1, 2], [3], []]; logits = torch.zeros((3, 8), dtype=torch.float32)
            prompt = torch.tensor([[1, 2], [2, 3], [0, 0]])
            p = torch.tensor([scale, 0.0, -scale]); f = torch.tensor([scale, 0.0, scale]); r = torch.tensor([1.0+scale, 1.0, 1.0+scale])
            out = apply_all_penalties(logits, prompt, p, f, r, rows)
            assert out.shape == logits.shape and torch.isfinite(out).all()


def _topk_topp_scenario():
    import torch
    from vllm.v1.sample.ops.topk_topp_sampler import TopKTopPSampler
    sampler = TopKTopPSampler()
    for k, p in [(2, 1.0), (4, 0.8), (None, 0.6)]:
        logits = torch.tensor([[0.1, 0.2, 0.3, 2.0], [1.0, 0.0, 0.5, -1.0]])
        kt = None if k is None else torch.tensor([k, k])
        pt = torch.tensor([p, p])
        sampled, returned = sampler.forward_cpu(logits, {}, kt, pt)
        assert tuple(sampled.shape) == (2,) and returned is None
        assert bool(((sampled >= 0) & (sampled < 4)).all())


def _remove_all_scenario():
    from vllm.v1.core.sched.utils import remove_all
    for values, remove, expected in [([1,2,3],[2],[1,3]), ([1,1,2],[1,3],[2]), ([],[],[])]:
        result = remove_all(values, set(remove)); assert result == expected


def _llm_scenario(case_id):
    os.environ.setdefault('VLLM_TARGET_DEVICE', 'cpu')
    os.environ.setdefault('VLLM_ENABLE_V1_MULTIPROCESSING', '0')
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    from vllm import LLM, SamplingParams
    kwargs = dict(model='facebook/opt-125m', enforce_eager=True,
                  max_model_len=64, max_num_seqs=4, gpu_memory_utilization=0.05,
                  enable_prefix_caching=True)
    if case_id in {'vllm-053', 'vllm-056', 'vllm-057'}:
        kwargs['speculative_config'] = {'method': 'ngram', 'num_speculative_tokens': 2,
                                        'prompt_lookup_min': 2, 'prompt_lookup_max': 4}
    llm = LLM(**kwargs)
    shared = 'alpha beta gamma delta ' * 8
    prompts = [shared + suffix for suffix in ('one', 'two', 'three')]
    stochastic = case_id in {'vllm-054', 'vllm-055'}
    params = [SamplingParams(max_tokens=n, temperature=0.8 if stochastic else 0.0,
                             top_k=5 if stochastic else -1,
                             top_p=0.8 if stochastic else 1.0, seed=10+n)
              for n in (1, 2, 3)]
    outputs = [llm.generate([prompt], param, use_tqdm=False)[0]
               for prompt, param in zip(prompts, params)]
    assert [o.prompt for o in outputs] == prompts
    assert all(1 <= len(o.outputs[0].token_ids) <= n
               for o, n in zip(outputs, (1, 2, 3)))
    # Reuse a prefix to create a concrete prefix-cache opportunity.
    more = llm.generate([shared + 'four', shared + 'five'],
                        SamplingParams(max_tokens=1, temperature=0.0), use_tqdm=False)
    assert len(more) == 2 and all(x.outputs for x in more)
    three = llm.generate([shared + suffix for suffix in ('six', 'seven', 'eight')],
                         SamplingParams(max_tokens=2, temperature=0.0), use_tqdm=False)
    assert len(three) == 3 and all(x.outputs for x in three)


def run(case_id):
    args = _args()
    sys.path.insert(0, args.source_root)
    from marker_probe import Probe
    probe = Probe()
    import vllm
    source_root = Path(args.source_root).resolve()
    loaded_root = Path(vllm.__file__).resolve()
    assert loaded_root.is_relative_to(source_root), (
        f'vllm imported from {loaded_root}, outside requested source root {source_root}')
    if 14 <= int(case_id[-3:]) <= 25:
        _queue_scenario(case_id)
    elif case_id == 'vllm-039':
        _remove_all_scenario()
    elif case_id == 'vllm-049':
        _request_scenario()
    elif case_id in {'vllm-050', 'vllm-051'}:
        _penalty_scenario(case_id)
    elif case_id == 'vllm-052':
        _topk_topp_scenario()
    else:
        _llm_scenario(case_id)
    probe.finish(case_id)
