"""Follow up the second pass: redundant precision scopes and layout feedback."""
import difflib
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
base=ROOT/'out/wan-gx/optimized-more';target=ROOT/'out/wan-gx/optimized-dispatch'
if target.exists(): raise SystemExit('Preserve optimized-dispatch before rerunning.')
shutil.copytree(base,target,ignore=shutil.ignore_patterns('__pycache__'))
p=target/'wan/modules/model.py';s=p.read_text()
# Removing cat also removed its contiguous result. Restore that layout once,
# instead of letting every layer norm pay for a conversion.
s=s.replace('            x = x[0]\n','            x = x[0].contiguous()\n')
start=s.index('class WanAttentionBlock');end=s.index('class Head',start)
part=s[start:end]
# These scopes contain only add/mul/chunk, all AutocastCUDA fallthrough ops.
assert part.count('with amp.autocast(enabled=False):') == 3
part=part.replace('''        with amp.autocast(enabled=False):
            e = (self.modulation + e).chunk(6, dim=1)''','''        e = (self.modulation + e).chunk(6, dim=1)''')
part=part.replace('''        with amp.autocast(enabled=False):
            x = x + y * e[2]''','''        x = x + y * e[2]''')
old='''        # cross-attention & ffn function
        def cross_attn_ffn(x, context, context_lens, e):
            x = x + self.cross_attn(self.norm3(x), context, context_lens)
            y = self.ffn(self.norm2(x).float() * (1 + e[4]) + e[3])
            with amp.autocast(enabled=False):
                x = x + y * e[5]
            return x

        x = cross_attn_ffn(x, context, context_lens, e)'''
new='''        x = x + self.cross_attn(self.norm3(x), context, context_lens)
        y = self.ffn(self.norm2(x).float() * (1 + e[4]) + e[3])
        x = x + y * e[5]'''
assert part.count(old)==1;part=part.replace(old,new);s=s[:start]+part+s[end:]
old='return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)'
assert s.count(old)==1
s=s.replace(old,'return torch.nn.functional.rms_norm(x, (self.dim,), eps=self.eps)')
p.write_text(s)
(ROOT/'examples/wan_gx/optimization-dispatch.patch').write_text(''.join(difflib.unified_diff(
    (base/'wan/modules/model.py').read_text().splitlines(True),s.splitlines(True),
    fromfile='a/wan/modules/model.py',tofile='b/wan/modules/model.py')))
print('Prepared',target)
