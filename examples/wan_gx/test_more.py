"""Second-pass math, layout, metadata, cache-lifetime and fallback checks on CPU."""
import os
os.environ.setdefault('WAN_OPTIMIZED_TREE','optimized-more')
from test_optimizations import *
import ast

# RoPE: full and padded sequences, single/multiple batches, varied input dtypes.
for batch,pad in ((1,0),(1,3),(2,0),(2,3)):
    grid=torch.tensor([[2,2,3]]*batch)
    freq=old.rope_params(16,8)
    for dtype in (torch.float32,torch.bfloat16):
        z=torch.randn(batch,12+pad,2,8).to(dtype)
        torch.testing.assert_close(new.rope_apply(z,grid,freq),old.rope_apply(z,grid,freq),rtol=0,atol=0)
# Per-frame convolutions: layout, groups, bias, spatial strides and temporal fallback.
for batch in (1,2):
    for groups in (1,2):
        for kt in (1,3):
            layer=torch.nn.Conv3d(4,6,(kt,2,2),stride=(1,2,2),groups=groups)
            z=torch.randn(batch,4,4,6,8)
            for x in (z,z.transpose(-1,-2)):
                torch.testing.assert_close(new.framewise_conv3d(layer,x),layer(x),rtol=1e-5,atol=1e-6)
# Run the actual attention preparation bodies against a CPU reference kernel.
# Only the CUDA-device assertion is removed; all packing/metadata code is real.
def cpu_attention(tree):
    module=load(tree,'attention')
    source=ast.parse((ROOT/tree/'wan/modules/attention.py').read_text())
    fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='flash_attention')
    fn.body=[n for n in fn.body if not (isinstance(n,ast.Assert) and "q.device.type" in ast.unparse(n))]
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(tree),'exec'),module.__dict__)
    module.FLASH_ATTN_2_AVAILABLE=True;module.FLASH_ATTN_3_AVAILABLE=False
    def reference(q,k,v,cu_seqlens_q,cu_seqlens_k,**kwargs):
        outputs=[]
        for qb,qe,kb,ke in zip(cu_seqlens_q[:-1],cu_seqlens_q[1:],cu_seqlens_k[:-1],cu_seqlens_k[1:]):
            qq,kk,vv=q[qb:qe],k[kb:ke],v[kb:ke]
            outputs.append(F.scaled_dot_product_attention(qq.transpose(0,1),kk.transpose(0,1),vv.transpose(0,1)).transpose(0,1))
        return torch.cat(outputs)
    module.flash_attn=types.SimpleNamespace(flash_attn_varlen_func=reference)
    return module
ba,ca=cpu_attention('baseline'),cpu_attention(CANDIDATE)
with ca.cache_attention_metadata():
    for batch in (1,2):
        for lengths in (None,torch.tensor([3]*batch),torch.tensor([5]*batch)):
            q=torch.randn(batch,4,2,8);k=torch.randn(batch,5,2,8);v=torch.randn_like(k)
            args=dict(q=q,k=k,v=v,k_lens=lengths)
            torch.testing.assert_close(ca.flash_attention(**args),ba.flash_attention(**args),rtol=0,atol=0)
    lengths=torch.tensor([2,5]);device=torch.device('cpu')
    first=ca.cumulative_lengths(lengths,2,5,device)
    assert ca.cumulative_lengths(lengths,2,5,device) is first
    lengths[0]=4
    torch.testing.assert_close(ca.cumulative_lengths(lengths,2,5,device),torch.tensor([0,4,9],dtype=torch.int32))
    assert len(ca._metadata_cache.get())>0
assert ca._metadata_cache.get() is None
try:
    with ca.cache_attention_metadata(): raise RuntimeError('deliberate')
except RuntimeError: pass
assert ca._metadata_cache.get() is None
print('PASS: exact RoPE full/padded B1/B2, framewise convolutions and fallback, real attention preparation with CPU kernel, metadata mutation/cleanup')

for dtype in (torch.float32,torch.bfloat16):
    for dim in (8,32,1536):
        before,after=old.WanRMSNorm(dim),new.WanRMSNorm(dim)
        after.load_state_dict(before.state_dict())
        x=torch.randn(2,7,dim).to(dtype)
        torch.testing.assert_close(after(x),before(x),rtol=1e-6,atol=1e-6)
print('PASS: RMSNorm float32/bfloat16 at dimensions 8, 32, 1536')
# The removed CUDA precision scopes only contained these operations. If the
# installed backend starts autocasting them, this optimization needs review.
for op in ('aten::add.Tensor','aten::mul.Tensor','aten::chunk'):
    lines=[s for s in torch._C._dispatch_dump_table(op).splitlines() if s.startswith('AutocastCUDA:')]
    assert len(lines)==1 and 'fallthrough' in lines[0], (op,lines)
print('PASS: removed precision scopes contain only AutocastCUDA fallthrough operations')
with torch.no_grad():
    for batch in (1,2):
        layer=torch.nn.Conv3d(4,6,(1,2,2),stride=(1,2,2),groups=2).to(torch.bfloat16)
        x=torch.randn(batch,4,4,6,8).to(torch.bfloat16)
        torch.testing.assert_close(new.framewise_conv3d(layer,x),layer(x),rtol=0,atol=0)
print('PASS: exact CPU bfloat16 framewise convolution outputs')
