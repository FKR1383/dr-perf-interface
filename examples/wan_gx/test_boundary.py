"""Execute real scheduler math on CPU; no numerical claims from GX tensors."""
import ast
import importlib.util
from pathlib import Path
import sys
import torch
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/wan-gx'

def load(label,tree):
    spec=importlib.util.spec_from_file_location(label,tree/'wan/utils/fm_solvers_unipc.py')
    module=importlib.util.module_from_spec(spec);sys.modules[label]=module;spec.loader.exec_module(module)
    return module.FlowUniPCMultistepScheduler

before,after=load('original_schedule',OUT/'upstream'),load('host_schedule',OUT/'baseline')
for steps in (4,6,50):
    old,new=before(num_train_timesteps=1000),after(num_train_timesteps=1000)
    for sched in (old,new): sched.set_timesteps(steps,device='cpu',shift=5.0)
    assert old.index_for_timestep(old.timesteps[0])==0
    new.set_begin_index(0)
    torch.manual_seed(42)
    a=torch.randn(1,4,3,2,2);b=a.clone()
    for t in old.timesteps:
        noise=torch.randn_like(a)
        a=old.step(noise,t,a,return_dict=False)[0]
        b=new.step(noise,t,b,return_dict=False)[0]
        torch.testing.assert_close(a,b,rtol=0,atol=0)
    assert new.step_index==steps and torch.isfinite(b).all()

# Execute the exact old/new __call__ bodies with deterministic CPU embeddings.
# This checks token trimming on varied padding without loading 11 GB of T5.
functions=[]
for tree in ('upstream','baseline'):
    code=ast.parse((OUT/tree/'wan/modules/t5.py').read_text())
    cls=next(n for n in code.body if isinstance(n,ast.ClassDef) and n.name=='T5EncoderModel')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__call__')
    namespace={'torch':torch}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(tree), 'exec'),namespace)
    functions.append(namespace['__call__'])
class Fake:
    def tokenizer(self,*a,**kw):
        ids=torch.arange(24).reshape(3,8)
        mask=torch.arange(8)[None,:]<torch.tensor([1,4,8])[:,None]
        return ids,mask.to(torch.int64)
    def model(self,ids,mask): return ids[:,:,None].expand(-1,-1,2).float()
old,new=[f(Fake(),['a','b','c'],'cpu') for f in functions]
assert [x.shape[0] for x in new]==[1,4,8]
for a,b in zip(old,new): torch.testing.assert_close(a,b,rtol=0,atol=0)
print('PASS: exact CPU scheduler outputs for 4/6/50 steps and token lengths 1/4/8')
