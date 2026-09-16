"""Remove redundant Wan CPU work without changing tensor operations or kernels."""
import difflib
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
base = root / 'out/wan-gx/baseline'
target = root / 'out/wan-gx/timing-cpu'
assert not target.exists(), 'Preserve existing experiments; use a fresh target'
shutil.copytree(base, target, ignore=shutil.ignore_patterns('__pycache__', '.git'))

def edit(relative, old, new):
    path = target / relative
    source = path.read_text()
    assert source.count(old) == 1, (relative, old[:80])
    path.write_text(source.replace(old, new))

# This pipeline never offloads or changes model residency inside the loop.
edit('wan/text2video.py', '                self.model.to(self.device)\n', '')
edit('wan/text2video.py', '            for _, t in enumerate(tqdm(timesteps)):',
     '            self.model.to(self.device)\n            for _, t in enumerate(tqdm(timesteps)):')

path = target / 'wan/modules/model.py'
source = path.read_text()
# float32 CUDA autocast already disables casting. Keep that disabled scope
# around linear layers, using the current API without a deprecation wrapper.
source = source.replace('amp.autocast(dtype=torch.float32)',
                        'torch.amp.autocast("cuda", dtype=torch.float32, enabled=False)')
start, end = source.index('class WanAttentionBlock'), source.index('class Head')
block = source[start:end]
for old, new in [
    ('        with torch.amp.autocast("cuda", dtype=torch.float32, enabled=False):\n'
     '            e = (self.modulation + e).chunk(6, dim=1)',
     '        e = (self.modulation + e).chunk(6, dim=1)'),
    ('        with torch.amp.autocast("cuda", dtype=torch.float32, enabled=False):\n'
     '            x = x + y * e[2]',
     '        x = x + y * e[2]'),
    ('''        # cross-attention & ffn function
        def cross_attn_ffn(x, context, context_lens, e):
            x = x + self.cross_attn(self.norm3(x), context, context_lens)
            y = self.ffn(self.norm2(x).float() * (1 + e[4]) + e[3])
            with torch.amp.autocast("cuda", dtype=torch.float32, enabled=False):
                x = x + y * e[5]
            return x

        x = cross_attn_ffn(x, context, context_lens, e)''',
     '''        x = x + self.cross_attn(self.norm3(x), context, context_lens)
        y = self.ffn(self.norm2(x).float() * (1 + e[4]) + e[3])
        x = x + y * e[5]'''),
]:
    assert block.count(old) == 1, old
    block = block.replace(old, new)
# Removed scopes contain only AutocastCUDA fallthrough add/mul/chunk.
source = source[:start] + block + source[end:]
path.write_text(source)
patch = []
for relative in ('wan/text2video.py', 'wan/modules/model.py'):
    patch.extend(difflib.unified_diff(
        (base / relative).read_text().splitlines(True),
        (target / relative).read_text().splitlines(True),
        fromfile='a/' + relative, tofile='b/' + relative))
(root / 'examples/wan_gx/optimization-timing-cpu.patch').write_text(''.join(patch))
print(target)
