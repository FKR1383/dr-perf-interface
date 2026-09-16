"""CPU value/operation checks for the fixed-kernel Wan application rewrite.

CUDA numerical equivalence is not claimed by this test. Autocast dispatcher
policy and the full GX launch inventory provide separate structural checks.
"""
import argparse
import importlib.util
from pathlib import Path
import sys
import types
import warnings
import torch
import torch.nn.functional as F
from torch.utils._python_dispatch import TorchDispatchMode

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--base', type=Path, default=Path('out/wan-gx/baseline'))
p.add_argument('--candidate', type=Path, default=Path('out/wan-gx/timing-cpu'))
a = p.parse_args()
torch.set_num_threads(1)
print('Validation torch:', torch.__version__, flush=True)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='User provided device_type of.*')

def load(root, prefix):
    for name, folder in ((prefix, root/'wan'), (prefix+'.modules', root/'wan/modules')):
        module = types.ModuleType(name)
        module.__path__ = [str(folder)]
        sys.modules[name] = module
    name = prefix+'.modules.model'
    spec = importlib.util.spec_from_file_location(name, root/'wan/modules/model.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

before, after = load(a.base, 'wan_before'), load(a.candidate, 'wan_after')
def reference_attention(q, k, v, **kwargs):
    mask = None
    if kwargs.get('k_lens') is not None:
        mask = (torch.arange(k.size(1))[None, :] < kwargs['k_lens'][:, None])[:, None, None, :]
    return F.scaled_dot_product_attention(q.transpose(1, 2), k.transpose(1, 2),
                                         v.transpose(1, 2), attn_mask=mask).transpose(1, 2).contiguous()
before.flash_attention = after.flash_attention = reference_attention
for op in ('aten::add.Tensor', 'aten::mul.Tensor', 'aten::chunk'):
    rows = [line for line in torch._C._dispatch_dump_table(op).splitlines()
            if line.startswith('AutocastCUDA:')]
    assert len(rows) == 1 and 'fallthrough' in rows[0], (op, rows)

class Operations(TorchDispatchMode):
    def __init__(self):
        super().__init__()
        self.calls = []
    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        self.calls.append(str(func))
        return func(*args, **(kwargs or {}))

torch.manual_seed(42)
config = dict(model_type='t2v', patch_size=(1,2,2), text_len=8, in_dim=4,
              dim=32, ffn_dim=64, freq_dim=16, text_dim=16, out_dim=4,
              num_heads=4, num_layers=2)
old, new = before.WanModel(**config).eval(), after.WanModel(**config).eval()
with torch.no_grad():
    old.head.head.weight.normal_(0, .1)
    old.head.head.bias.normal_(0, .1)
new.load_state_dict(old.state_dict())
checks = 0
with torch.no_grad():
    for batch in (1,2):
        for padding in (0,3):
            for step in (0,1,2):
                args = dict(x=[torch.randn(4,3,4,6) for _ in range(batch)],
                            t=torch.tensor([100.-step]*batch),
                            context=[torch.randn(3+i,16) for i in range(batch)],
                            seq_len=18+padding)
                with Operations() as left:
                    expected = old(**args)
                with Operations() as right:
                    actual = new(**args)
                assert left.calls == right.calls, 'Tensor operation sequence changed'
                for x, y in zip(actual, expected):
                    assert x.count_nonzero() > 0
                    torch.testing.assert_close(x, y, rtol=0, atol=0)
                checks += 1
print(f'PASS: {checks} nonzero transformer comparisons, exact CPU outputs and tensor operation sequences; CUDA autocast fallthrough policy')
