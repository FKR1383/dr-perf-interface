"""CPU numerical checks for application rewrites, separate from GX structural runs."""
import importlib.util
import os
from pathlib import Path
import sys
import types
import torch
import torch.nn.functional as F
CANDIDATE=os.environ.get('WAN_OPTIMIZED_TREE','optimized')
ROOT=Path(__file__).resolve().parents[2]/'out/wan-gx'

def load(tree,module):
    prefix='test_'+tree
    for name,folder in [(prefix,ROOT/tree/'wan'),(prefix+'.modules',ROOT/tree/'wan/modules')]:
        if name not in sys.modules:
            package=types.ModuleType(name);package.__path__=[str(folder)];sys.modules[name]=package
    name=prefix+'.modules.'+module
    spec=importlib.util.spec_from_file_location(name,ROOT/tree/'wan/modules'/f'{module}.py')
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

old,new=load('baseline','model'),load(CANDIDATE,'model')
# CPU reference attention validates tensor semantics, not CUDA kernel rounding.
def attention(q,k,v,**kw):
    mask=None
    lengths=kw.get('k_lens')
    if lengths is not None:
        mask=torch.arange(k.shape[1])[None,:]<lengths[:,None]
        mask=mask[:,None,None,:]
    return F.scaled_dot_product_attention(q.transpose(1,2),k.transpose(1,2),v.transpose(1,2),attn_mask=mask).transpose(1,2).contiguous()
old.flash_attention=new.flash_attention=attention
cfg=dict(model_type='t2v',patch_size=(1,2,2),text_len=8,in_dim=4,dim=32,ffn_dim=64,
         freq_dim=16,text_dim=16,out_dim=4,num_heads=4,num_layers=2)
torch.manual_seed(42)
a,b=old.WanModel(**cfg).eval(),new.WanModel(**cfg).eval()
b.load_state_dict(a.state_dict())
# The shipped constructor zeroes the output head. Randomize it so a broken
# internal computation cannot pass by producing a constant zero output.
with torch.no_grad():
    a.head.head.weight.normal_(0,.1);a.head.head.bias.normal_(0,.1)
b.load_state_dict(a.state_dict())
x=[torch.randn(4,3,4,6)]; contexts=[[torch.randn(n,16)] for n in (3,7)]
with torch.no_grad():
    for generation in range(2):
        with b.cpu_work_cache():
            for step in range(3):
                for context in contexts:
                    args=dict(x=x,t=torch.tensor([100.-step]),context=context,seq_len=18)
                    expected=a(**args);actual=b(**args)
                    torch.testing.assert_close(actual,expected,rtol=1e-6,atol=1e-6)
                if step==1: contexts[0][0].add_(.25)
            assert len(b._cpu_context_cache)==3
        assert b._cpu_context_cache is None
        assert all(block.cross_attn._cpu_kv_cache is None for block in b.blocks)
    try:
        with b.cpu_work_cache(): raise RuntimeError('deliberate')
    except RuntimeError: pass
    assert b._cpu_context_cache is None

ov,nv=load('baseline','vae'),load(CANDIDATE,'vae')
va=ov.WanVAE_(dim=4,z_dim=4,dim_mult=[1,2],num_res_blocks=1,temperal_downsample=[False]).eval()
vb=nv.WanVAE_(dim=4,z_dim=4,dim_mult=[1,2],num_res_blocks=1,temperal_downsample=[False]).eval()
vb.load_state_dict(va.state_dict())
with torch.no_grad():
    for frames in (1,3,5):
        z=torch.randn(1,4,frames,2,2)
        torch.testing.assert_close(va.decode(z,[0.,1.]),vb.decode(z,[0.,1.]),rtol=0,atol=0)
print('PASS: 12 nonzero transformer outputs, context mutation, cache cleanup, VAE decode 1/3/5 chunks')
attention_module=load(CANDIDATE,'attention')
for dtype in (torch.float32,torch.bfloat16):
    for lens in ([5],[3],[0],[5,5],[2,5],[0,4]):
        x=torch.randn(len(lens),5,3,4,dtype=dtype)
        lengths=torch.tensor(lens)
        expected=torch.cat([u[:n] for u,n in zip(x,lengths)])
        actual=attention_module.pack_kv(x,lengths)
        torch.testing.assert_close(actual,expected,rtol=0,atol=0)
        if all(n==5 for n in lens): assert actual.data_ptr()==x.data_ptr()
print('PASS: full/ragged/empty attention packing, batches 1/2, float32/bfloat16')
