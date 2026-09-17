"""Second pass, driven by the residual costs in evidence/optimized.json."""
import difflib
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
base=ROOT/'out/wan-gx/optimized';target=ROOT/'out/wan-gx/optimized-more'
if target.exists(): raise SystemExit('Preserve the existing optimized-more tree before rerunning.')
shutil.copytree(base,target,ignore=shutil.ignore_patterns('__pycache__'))
def edit(rel,old,new):
    p=target/rel;s=p.read_text();assert s.count(old)==1,(rel,old[:80],s.count(old));p.write_text(s.replace(old,new))
p='wan/modules/attention.py'
edit(p,'import torch\n','import torch\nfrom contextlib import contextmanager\nfrom contextvars import ContextVar\n')
helper='''_metadata_cache = ContextVar('wan_attention_metadata', default=None)


@contextmanager
def cache_attention_metadata():
    token = _metadata_cache.set({})
    try:
        yield
    finally:
        _metadata_cache.reset(token)


def cumulative_lengths(lengths, batch, full_length, device):
    # CPU-owned lengths require no device arithmetic or device-to-host read.
    if lengths is not None and lengths.device.type != 'cpu':
        return torch.cat([lengths.new_zeros([1]), lengths]).cumsum(
            0, dtype=torch.int32).to(device, non_blocking=True)
    values = tuple(lengths.tolist()) if lengths is not None else (full_length,) * batch
    key = (device, values)
    cache = _metadata_cache.get()
    if cache is not None and key in cache:
        return cache[key]
    prefix = [0]
    for length in values:
        prefix.append(prefix[-1] + length)
    result = torch.tensor(prefix, dtype=torch.int32, device=device)
    if cache is not None:
        cache[key] = result
    return result


'''
edit(p,'def pack_kv(',helper+'def pack_kv(')
edit(p,'''        q_lens = torch.tensor(
            [lq] * b, dtype=torch.int32).to(
                device=q.device, non_blocking=True)
''','')
edit(p,'''        k_lens = torch.tensor(
            [lk] * b, dtype=torch.int32).to(
                device=k.device, non_blocking=True)
''','')
# Identical values and same varlen FlashAttention entry point, with reused metadata.
s=(target/p).read_text()
for name,full in [('q','lq'),('k','lk')]:
    old=f'''torch.cat([{name}_lens.new_zeros([1]), {name}_lens]).cumsum(
                0, dtype=torch.int32).to(q.device, non_blocking=True)'''
    assert s.count(old)==2
    s=s.replace(old,f'cumulative_lengths({name}_lens, b, {full}, q.device)')
(target/p).write_text(s)

p='wan/modules/model.py'
edit(p,'from .attention import flash_attention','from .attention import flash_attention, cache_attention_metadata')
edit(p,'        self._cpu_context_cache = {}','        self._cpu_context_cache = {}\n        self._cpu_rope_cache = {}')
edit(p,'''        try:
            yield
        finally:
            self._cpu_context_cache = None''','''        try:
            with cache_attention_metadata():
                yield
        finally:
            self._cpu_rope_cache = None
            self._cpu_context_cache = None''')
helper='''    def cached_rope_grids(self, grid_sizes):
        if torch.is_grad_enabled():
            return self.freqs
        cache = getattr(self, '_cpu_rope_cache', None)
        key = (tuple(map(tuple, grid_sizes.tolist())), id(self.freqs), self.freqs._version)
        if cache is None:
            return rope_grid_frequencies(grid_sizes, self.freqs)
        if key not in cache:
            cache[key] = rope_grid_frequencies(grid_sizes, self.freqs)
        return cache[key]

'''
edit(p,'    @contextmanager\n    def cpu_work_cache',helper+'    @contextmanager\n    def cpu_work_cache')
edit(p,'freqs=rope_grid_frequencies(grid_sizes, self.freqs) if not torch.is_grad_enabled() else self.freqs,',
       'freqs=self.cached_rope_grids(grid_sizes),')
edit(p,'    # loop over samples\n    output = []','''    # The common single, unpadded sequence needs no slice/cat/stack copies.
    if x.size(0) == 1 and grids[0].size(0) == x.size(1):
        z = torch.view_as_complex(x.to(torch.float64).reshape(1, x.size(1), n, c, 2))
        return torch.view_as_real(z * grids[0]).flatten(3).float()

    # loop over samples
    output = []''')
old='''        x = torch.cat([
            torch.cat([u, u.new_zeros(1, seq_len - u.size(1), u.size(2))],
                      dim=1) for u in x
        ])'''
new='''        if len(x) == 1 and x[0].size(1) == seq_len:
            x = x[0]
        else:
            x = torch.cat([
                torch.cat([u, u.new_zeros(1, seq_len - u.size(1), u.size(2))],
                          dim=1) for u in x
            ])'''
edit(p,old,new)
# float32 CUDA autocast disables casting. Express that intent directly.
s=(target/p).read_text();s=s.replace('amp.autocast(dtype=torch.float32)','amp.autocast(enabled=False)');(target/p).write_text(s)
# Temporal kernel/stride/dilation of one is independent per frame.
helper='''def framewise_conv3d(layer, x):
    if (layer.kernel_size[0], layer.stride[0], layer.padding[0], layer.dilation[0]) != (1, 1, 0, 1):
        return layer(x)
    b, c, t, h, w = x.shape
    frames = x.permute(0, 2, 1, 3, 4).reshape(b * t, c, h, w)
    y = torch.nn.functional.conv2d(frames, layer.weight[:, :, 0], layer.bias,
                                  layer.stride[1:], layer.padding[1:], layer.dilation[1:], layer.groups)
    return y.reshape(b, t, y.size(1), y.size(2), y.size(3)).permute(0, 2, 1, 3, 4)


'''
edit(p,'class WanModel(ModelMixin, ConfigMixin):',helper+'class WanModel(ModelMixin, ConfigMixin):')
edit(p,'x = [self.patch_embedding(u.unsqueeze(0)) for u in x]',
       'x = [framewise_conv3d(self.patch_embedding, u.unsqueeze(0)) for u in x]')
p='wan/modules/vae.py'
edit(p,'        x = F.pad(x, padding)','        if any(padding):\n            x = F.pad(x, padding)')
pieces=[]
for rel in ('wan/modules/attention.py','wan/modules/model.py','wan/modules/vae.py'):
    pieces.extend(difflib.unified_diff((base/rel).read_text().splitlines(True),
        (target/rel).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(ROOT/'examples/wan_gx/optimization-more.patch').write_text(''.join(pieces))
print('Prepared',target)
