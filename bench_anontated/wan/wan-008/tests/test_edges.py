"""Reference-loop edge checks for wan-008."""
import argparse, pathlib, sys
from marker_probe import Probe
p=argparse.ArgumentParser();p.add_argument("--source-root",required=True);a=p.parse_args();probe=Probe()
sys.path.insert(0,str(pathlib.Path(a.source_root).resolve()/"src"))
import torch
from diffusers import AutoencoderKLWan
torch.set_grad_enabled(False);torch.set_num_threads(1);torch.manual_seed(29)
vae=AutoencoderKLWan(base_dim=8,z_dim=16,dim_mult=[1,2,4,4],num_res_blocks=1,attn_scales=[],temperal_downsample=[False,True,True],scale_factor_temporal=4,scale_factor_spatial=8).eval()
horizontal=False
def reference(x,y,extent):
 extent=min(x.shape[-1 if horizontal else -2],y.shape[-1 if horizontal else -2],extent)
 for i in range(extent):
  if horizontal:y[:,:,:,:,i]=x[:,:,:,:,-extent+i]*(1-i/extent)+y[:,:,:,:,i]*(i/extent)
  else:y[:,:,:,i,:]=x[:,:,:,-extent+i,:]*(1-i/extent)+y[:,:,:,i,:]*(i/extent)
 return y
def actual(x,y,extent):return vae.blend_h(x,y,extent) if horizontal else vae.blend_v(x,y,extent)
for dtype,tol in ((torch.float64,1e-12),(torch.float32,1e-6),(torch.float16,1e-3),(torch.bfloat16,1e-2)):
 for extent in (-1,0,1,2,3):
  x=torch.randn(1,2,2,5,5,dtype=dtype);y=torch.randn_like(x)
  assert torch.allclose(actual(x.clone(),y.clone(),extent),reference(x.clone(),y.clone(),extent),rtol=tol,atol=tol)
x=torch.randn(1,2,2,5,5);y=x.clone();assert torch.equal(actual(y,y,3),reference(x,x,3))
probe.finish("wan-008")
