import os
import torch
import perfmark
print('torch',torch.__version__,'cuda',torch.cuda.is_available(),flush=True)
x=torch.empty((16,16),device='cuda')
for n in (1,2,3):
    with perfmark.region('gx_smoke',n=n):
        for _ in range(n): x=x+x
print('smoke completed',x.shape,flush=True)
