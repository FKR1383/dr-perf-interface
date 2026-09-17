"""Complete official WanT2V pipeline, with optional matched CPU instrumentation."""
import argparse
import json
import hashlib
import importlib.metadata
import os
from pathlib import Path
import sys
import time
p=argparse.ArgumentParser()
p.add_argument('--tree',required=True)
p.add_argument('--frames',type=int,default=int(os.environ.get('WAN_FRAMES',81)))
p.add_argument('--steps',type=int,default=int(os.environ.get('WAN_STEPS',50)))
p.add_argument('--repeats',type=int,default=1)
p.add_argument('--mark',action='store_true')
p.add_argument('--conv-backend',choices=('cudnn','native'),default='cudnn')
p.add_argument('--output',required=True)
a=p.parse_args()
sys.path.insert(0,a.tree)
import torch
if a.conv_backend=='native': torch.backends.cudnn.enabled=False
import wan
from wan.configs import WAN_CONFIGS
root=Path(__file__).resolve().parents[2]
assert Path(wan.__file__).resolve().is_relative_to(Path(a.tree).resolve())
assert os.environ.get('WAN_MODEL','Wan-AI/Wan2.1-T2V-1.3B')=='Wan-AI/Wan2.1-T2V-1.3B'
assert os.environ.get('GX_COMM_ONLY')=='1', 'This experiment requires GX emu-only.'
assert not any(k.startswith('GXVM_') for k in os.environ), 'Timing simulation must be off.'
assert not any(os.environ.get(k) for k in ('GX_PREDICT_DB','NEX_PREDICT_DB','GX_PROFILE_DB','NEX_PROFILE_DB'))
width,height=map(int,os.environ.get('WAN_SIZE','832*480').split('*'))
prompt=os.environ.get('WAN_PROMPT','A cat walks on the grass, realistic style')
seed=int(os.environ.get('WAN_SEED',42))
offload=os.environ.get('WAN_OFFLOAD','False')=='True'
t0=time.monotonic()
pipe=wan.WanT2V(config=WAN_CONFIGS['t2v-1.3B'],checkpoint_dir=str(root/'out/wan-gx/checkpoint'))
load=time.monotonic()-t0
regions=[]
if a.mark:
    from instrument import install
    regions=install(pipe)
records=[]
for repeat in range(a.repeats):
    start=time.monotonic()
    video=pipe.generate(prompt,size=(width,height),frame_num=a.frames,
                        sampling_steps=a.steps,sample_solver='unipc',shift=5.0,guide_scale=5.0,
                        seed=seed,offload_model=offload)
    torch.cuda.synchronize()
    assert tuple(video.shape)==(3,a.frames,height,width),video.shape
    records.append({'repeat':repeat,'generation_host_seconds':time.monotonic()-start,'shape':list(video.shape)})
    del video
report={'tree':a.tree,'frames':a.frames,'steps':a.steps,'load_seconds':load,'runs':records,
        'regions':regions,'numerical_validation':False,'timing_simulation':False,'torch':torch.__version__,
        'convolution_backend':a.conv_backend,'size':[width,height],'prompt':prompt,'seed':seed,'offload':offload,
        'gx_comm_only':os.environ.get('GX_COMM_ONLY'),
        'source_sha256':{str(p.relative_to(a.tree)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(Path(a.tree).rglob('*.py'))},
        'drperf_binary_sha256':hashlib.sha256((root/'build/libdrperf.so').read_bytes()).hexdigest(),
        'packages':{k:importlib.metadata.version(k) for k in ('torch','diffusers','transformers','flash-attn','safetensors')},
        'policy':json.loads((root/'out/wan-gx/policy.json').read_text())}
Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
