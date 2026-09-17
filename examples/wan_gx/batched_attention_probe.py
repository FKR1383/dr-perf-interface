"""Isolate the two batched matrix products in Wan's T5 attention."""
import os
from pathlib import Path
import torch
if os.environ.get('CUDNN_LOGDEST_DBG'):
    os.chdir(Path(os.environ['CUDNN_LOGDEST_DBG']).parent)
torch.set_num_threads(1)
q, k, v = [torch.zeros((1,512,64,64),dtype=torch.bfloat16,device='cuda') for _ in range(3)]
print('T5_QK_BEGIN',flush=True)
attn = torch.einsum('binc,bjnc->bnij',q,k)
torch.cuda.synchronize()
print('T5_QK_END',list(attn.shape),flush=True)
print('T5_AV_BEGIN',flush=True)
x = torch.einsum('bnij,bjnc->binc',attn,v)
torch.cuda.synchronize()
print('T5_AV_END',list(x.shape),flush=True)
