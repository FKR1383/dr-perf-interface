"""Create isolated Wan copies and retain exact source patches."""
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/wan-gx'
PIN='9737cba9c1c3c4d04b33fcad41c111989865d315'
assert subprocess.check_output(['git','-C',str(OUT/'upstream'),'rev-parse','HEAD'],text=True).strip()==PIN

def replace(path,old,new):
    s=path.read_text(); assert s.count(old)==1,(path,old[:60],s.count(old));path.write_text(s.replace(old,new))

base=OUT/'baseline'
if not base.exists(): shutil.copytree(OUT/'upstream',base,ignore=shutil.ignore_patterns('.git','__pycache__'))
# Both variants retain host-owned control metadata on the host. No GPU model
# arithmetic is replaced, and timestep/CFG/decoder calls remain intact.
if '        mask = mask.to(device)\n        seq_lens = mask.gt(0)' in (base/'wan/modules/t5.py').read_text():
    replace(base/'wan/modules/t5.py',
            '        ids = ids.to(device)\n        mask = mask.to(device)\n        seq_lens = mask.gt(0).sum(dim=1).long()',
            '        seq_lens = mask.gt(0).sum(dim=1).long()\n        ids = ids.to(device)\n        mask = mask.to(device)')
    replace(base/'wan/text2video.py',
            "            # sample videos\n            latents = noise",
            "            # Full text-to-video generation starts at the first scheduled step.\n            sample_scheduler.set_begin_index(0)\n\n            # sample videos\n            latents = noise")
scheduler=base/'wan/utils/fm_solvers_unipc.py'
s=scheduler.read_text()
assert s.count('rks = torch.tensor(rks, device=device)') in (0,2)
assert s.count('b = torch.tensor(b, device=device)') in (0,2)
s=s.replace('rks = torch.tensor(rks, device=device)', 'rks = torch.tensor(rks, device="cpu")')
s=s.replace('b = torch.tensor(b, device=device)', 'b = torch.tensor(b, device="cpu")')
scheduler.write_text(s)
# Emit a reviewable common patch without modifying the pinned checkout.
pieces=[]
for rel in ['wan/modules/t5.py','wan/text2video.py','wan/utils/fm_solvers_unipc.py']:
    import difflib
    pieces.extend(difflib.unified_diff((OUT/'upstream'/rel).read_text().splitlines(True),
                                     (base/rel).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(ROOT/'examples/wan_gx/metadata.patch').write_text(''.join(pieces))
print('Prepared baseline with explicit CPU control-metadata patch:',base)
