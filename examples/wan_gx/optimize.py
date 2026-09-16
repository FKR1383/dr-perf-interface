"""Apply reviewable application optimizations to an isolated boundary-fixed tree."""
import difflib
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'out/wan-gx'
base=OUT/'baseline';target=OUT/'optimized'
if target.exists(): raise SystemExit('Optimized tree already exists; move it aside to preserve it before rerunning.')
shutil.copytree(base,target,ignore=shutil.ignore_patterns('__pycache__'))

def edit(rel,old,new):
    p=target/rel;s=p.read_text();assert s.count(old)==1,(rel,old[:70],s.count(old));p.write_text(s.replace(old,new))

# Residency cannot change inside this fixed, single-device denoising loop.
p='wan/text2video.py'
edit(p,'                self.model.to(self.device)\n','')
edit(p,'            for _, t in enumerate(tqdm(timesteps)):',
       '            self.model.to(self.device)\n            for _, t in enumerate(tqdm(timesteps)):')
# Limit inference caches to one generation, releasing on success or exception.
s=(target/p).read_text();begin=s.index('            self.model.to(self.device)\n            for _, t')
end=s.index('\n            x0 = latents',begin)
s=s[:begin]+'            with self.model.cpu_work_cache():\n'+''.join('    '+line if line.strip() else line for line in s[begin:end].splitlines(True))+s[end:]
(target/p).write_text(s)

p='wan/modules/model.py'
edit(p,'import math\n','import math\nfrom contextlib import contextmanager\n')
helper='''def rope_grid_frequencies(grid_sizes, freqs):
    c = freqs.shape[1]
    parts = freqs.split([c - 2 * (c // 3), c // 3, c // 3], dim=1)
    grids = []
    for f, h, w in grid_sizes.tolist():
        grids.append(torch.cat([
            parts[0][:f].view(f, 1, 1, -1).expand(f, h, w, -1),
            parts[1][:h].view(1, h, 1, -1).expand(f, h, w, -1),
            parts[2][:w].view(1, 1, w, -1).expand(f, h, w, -1)
        ], dim=-1).reshape(f * h * w, 1, -1))
    return tuple(grids)


'''
edit(p,'@amp.autocast(enabled=False)\ndef rope_apply',helper+'@amp.autocast(enabled=False)\ndef rope_apply')
edit(p,'    freqs = freqs.split([c - 2 * (c // 3), c // 3, c // 3], dim=1)',
       '    grids = freqs if isinstance(freqs, tuple) else rope_grid_frequencies(grid_sizes, freqs)')
old='''        freqs_i = torch.cat([
            freqs[0][:f].view(f, 1, 1, -1).expand(f, h, w, -1),
            freqs[1][:h].view(1, h, 1, -1).expand(f, h, w, -1),
            freqs[2][:w].view(1, 1, w, -1).expand(f, h, w, -1)
        ],
                            dim=-1).reshape(seq_len, 1, -1)'''
edit(p,old,'        freqs_i = grids[i]')
edit(p,'            freqs=self.freqs,',
       '            freqs=rope_grid_frequencies(grid_sizes, self.freqs) if not torch.is_grad_enabled() else self.freqs,')
# Cache inputs are retained by the generation, preventing identity reuse.
method='''    @contextmanager
    def cpu_work_cache(self):
        if self.training or torch.is_grad_enabled():
            yield
            return
        self._cpu_context_cache = {}
        for block in self.blocks:
            block.cross_attn._cpu_kv_cache = {}
        try:
            yield
        finally:
            self._cpu_context_cache = None
            for block in self.blocks:
                block.cross_attn._cpu_kv_cache = None

'''
edit(p,'    def unpatchify(self, x, grid_sizes):',method+'    def unpatchify(self, x, grid_sizes):')
old='''        context = self.text_embedding(
            torch.stack([
                torch.cat(
                    [u, u.new_zeros(self.text_len - u.size(0), u.size(1))])
                for u in context
            ]))'''
new='''        cache = getattr(self, '_cpu_context_cache', None)
        key = tuple((id(u), u._version) for u in context)
        cached = cache.get(key) if cache is not None else None
        if cached is None:
            source_context = context
            context = self.text_embedding(
                torch.stack([
                    torch.cat([u, u.new_zeros(self.text_len - u.size(0), u.size(1))])
                    for u in context
                ]))
            if cache is not None:
                cache[key] = (source_context, context)
        else:
            context = cached[1]'''
edit(p,old,new)
# Only alter the T2V cross-attention definition (the I2V path is untouched).
s=(target/p).read_text();start=s.index('class WanT2VCrossAttention');end=s.index('class WanI2VCrossAttention',start)
part=s[start:end]
old='''        k = self.norm_k(self.k(context)).view(b, -1, n, d)
        v = self.v(context).view(b, -1, n, d)'''
new='''        cache = getattr(self, '_cpu_kv_cache', None)
        key = (id(context), context._version)
        cached = cache.get(key) if cache is not None else None
        if cached is None:
            k = self.norm_k(self.k(context)).view(b, -1, n, d)
            v = self.v(context).view(b, -1, n, d)
            if cache is not None:
                cache[key] = (context, k, v)
        else:
            _, k, v = cached'''
assert part.count(old)==1;part=part.replace(old,new);(target/p).write_text(s[:start]+part+s[end:])

p='wan/modules/vae.py'
old='''        for i in range(iter_):
            self._conv_idx = [0]
            if i == 0:
                out = self.decoder(
                    x[:, :, i:i + 1, :, :],
                    feat_cache=self._feat_map,
                    feat_idx=self._conv_idx)
            else:
                out_ = self.decoder(
                    x[:, :, i:i + 1, :, :],
                    feat_cache=self._feat_map,
                    feat_idx=self._conv_idx)
                out = torch.cat([out, out_], 2)'''
new='''        chunks = []
        for i in range(iter_):
            self._conv_idx = [0]
            chunks.append(self.decoder(
                x[:, :, i:i + 1, :, :],
                feat_cache=self._feat_map,
                feat_idx=self._conv_idx))
        out = chunks[0] if len(chunks) == 1 else torch.cat(chunks, 2)'''
edit(p,old,new)
# Topology is static for this inference application; count once per instance.
edit(p,'        self._conv_num = count_conv3d(self.decoder)',
       "        if not hasattr(self, '_conv_num'):\n            self._conv_num = count_conv3d(self.decoder)")
edit(p,'        self._enc_conv_num = count_conv3d(self.encoder)',
       "        if not hasattr(self, '_enc_conv_num'):\n            self._enc_conv_num = count_conv3d(self.encoder)")

p='wan/modules/attention.py'
helper='\n\ndef pack_kv(x, lengths):\n    if lengths.device.type == "cpu" and lengths.tolist() == [x.shape[1]] * x.shape[0]:\n        return x.flatten(0, 1)\n    return torch.cat([u[:n] for u, n in zip(x, lengths)])\n\n\n'
edit(p,'def flash_attention(',helper+'def flash_attention(')
edit(p,'k = half(torch.cat([u[:v] for u, v in zip(k, k_lens)]))','k = half(pack_kv(k, k_lens))')
edit(p,'v = half(torch.cat([u[:v] for u, v in zip(v, k_lens)]))','v = half(pack_kv(v, k_lens))')

pieces=[]
for rel in ('wan/text2video.py','wan/modules/model.py','wan/modules/vae.py','wan/modules/attention.py'):
    pieces.extend(difflib.unified_diff((base/rel).read_text().splitlines(True),
                                     (target/rel).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(ROOT/'examples/wan_gx/optimization.patch').write_text(''.join(pieces))
print('Prepared',target)
